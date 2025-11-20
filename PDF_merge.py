import streamlit as st
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from pypdf.generic import AnnotationBuilder
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def create_toc_page(entries):
    """
    entries: [{"title": str, "start_page": int}, ...]
    start_page 는 사람 기준 페이지 번호 (1부터 시작, TOC 포함)
    반환값:
      toc_pdf_bytes: 목차만 있는 PDF 바이트
      link_positions: 각 항목의 y좌표 리스트 (PDF 좌표계, bottom-left 기준)
      page_width: 페이지 가로 길이
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 72, "목차 (Table of Contents)")

    c.setFont("Helvetica", 12)
    y = height - 110

    link_positions = []

    for i, entry in enumerate(entries, start=1):
        line = f"{i}. {entry['title']}  ......  p. {entry['start_page']}"
        c.drawString(80, y, line)
        link_positions.append(y)  # 나중에 링크 영역을 만들기 위해 y좌표 저장
        y -= 18
        # 매우 많은 파일을 올리지 않는다는 가정 하에, 여기서는 1페이지 목차만 처리

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue(), link_positions, width


def merge_pdfs_with_toc(uploaded_files):
    # 1. 각 PDF 정보 읽기
    pdf_infos = []
    for uf in uploaded_files:
        reader = PdfReader(uf)
        num_pages = len(reader.pages)
        pdf_infos.append(
            {
                "name": uf.name,
                "reader": reader,
                "num_pages": num_pages,
            }
        )

    # 2. 사람 기준 페이지 번호 계산 (1페이지는 목차)
    entries = []
    current_page = 1  # TOC 페이지
    for info in pdf_infos:
        start_page = current_page + 1  # TOC 다음 페이지가 병합된 PDF의 2페이지
        entries.append(
            {
                "title": info["name"],
                "start_page": start_page,
            }
        )
        current_page += info["num_pages"]

    # 3. 목차 페이지 PDF 생성 + 각 항목의 y좌표 기록
    toc_pdf_bytes, link_positions, toc_page_width = create_toc_page(entries)
    toc_reader = PdfReader(BytesIO(toc_pdf_bytes))

    # 4. 최종 PDF 작성
    writer = PdfWriter()

    # 4-1. 목차 페이지 추가 (0번 페이지)
    for page in toc_reader.pages:
        writer.add_page(page)

    # 4-2. 실제 PDF 페이지들 추가
    start_page_indices = []  # writer 기준 0-based index
    for info in pdf_infos:
        start_index = len(writer.pages)  # 이 파일이 시작되는 페이지 인덱스
        start_page_indices.append(start_index)
        for page in info["reader"].pages:
            writer.add_page(page)

    # 5. 북마크(Outline) 추가: 왼쪽 사이드 패널에 파일 단위 북마크
    for info, page_index in zip(pdf_infos, start_page_indices):
        writer.add_outline_item(info["name"], page_index)

    # 6. 목차 페이지에 "클릭 가능한 링크" 추가
    #    AnnotationBuilder.link 를 이용해서 내부 링크(Internal link) 생성
    for i, (entry, y) in enumerate(zip(entries, link_positions)):
        target_page_index = start_page_indices[i]  # 이동해야 할 페이지 (0-based)

        # 클릭 영역 사각형 설정: [xLL, yLL, xUR, yUR]
        # 텍스트 왼쪽 여백보다 약간 왼쪽/오른쪽으로 넉넉하게 잡음
        rect = (
            70,          # xLL
            y - 2,       # yLL
            toc_page_width - 70,  # xUR
            y + 12       # yUR
        )

        annotation = AnnotationBuilder.link(
            rect=rect,
            target_page_index=target_page_index,
        )

        # page_number=0 이므로 TOC 페이지에 이 링크 주석을 추가
        writer.add_annotation(page_number=0, annotation=annotation)

    # 7. 결과 PDF 바이트로 반환
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.getvalue()


def main():
    st.title("PDF 병합 + 클릭 가능한 목차 생성 앱")
    st.write("여러 PDF를 업로드하면 하나로 병합하고, 첫 페이지에 목차와 북마크를 만듭니다.")
    st.write("목차에서 제목을 클릭하면 각 PDF의 첫 페이지로 바로 이동할 수 있습니다.")

    uploaded_files = st.file_uploader(
        "PDF 파일을 여러 개 선택하세요.",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.write("업로드된 파일:")
        for uf in uploaded_files:
            st.write(f"- {uf.name}")

        if st.button("병합 PDF 생성하기"):
            merged_pdf = merge_pdfs_with_toc(uploaded_files)

            st.success("병합이 완료되었습니다! (목차 클릭 시 해당 페이지로 이동 가능)")
            st.download_button(
                label="병합된 PDF 다운로드",
                data=merged_pdf,
                file_name="merged_with_clickable_toc.pdf",
                mime="application/pdf",
            )


if __name__ == "__main__":
    main()
