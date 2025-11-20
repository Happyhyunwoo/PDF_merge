import streamlit as st
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link   # ✅ 새로 추가
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def create_toc_page(entries):
    """
    entries: [{"title": str, "start_page": int}, ...]
    start_page 는 사람 기준 1, 2, 3 페이지 번호 (TOC 포함)
    반환:
      toc_bytes: 목차 PDF의 바이트
      link_positions: 각 항목의 y 좌표 리스트
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
        # 나중에 이 줄 전체를 클릭 영역으로 만들기 위해 y 좌표 저장
        link_positions.append(y)
        y -= 18
        if y < 72:
            break  # 예제에서는 목차를 1페이지로 제한

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue(), link_positions, width


def merge_pdfs_with_toc(uploaded_files):
    # 1. 각 PDF의 페이지 수 계산
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

    # 2. 각 PDF의 시작 페이지 번호 계산 (사람 기준, 1페이지는 목차)
    entries = []
    current_page = 1  # 1페이지는 TOC
    for info in pdf_infos:
        start_page = current_page + 1  # TOC 다음 페이지가 2페이지
        entries.append(
            {
                "title": info["name"],
                "start_page": start_page,
            }
        )
        current_page += info["num_pages"]

    # 3. 목차 페이지 PDF 생성 + 링크용 y좌표 정보
    toc_pdf_bytes, link_positions, toc_page_width = create_toc_page(entries)
    toc_reader = PdfReader(BytesIO(toc_pdf_bytes))

    # 4. 최종 병합 PDF 생성
    writer = PdfWriter()

    # 4-1. 목차 페이지 추가 (0번 페이지)
    for page in toc_reader.pages:
        writer.add_page(page)

    # 4-2. 업로드한 모든 PDF 페이지 추가
    start_page_indices = []  # writer 기준 0-based index
    for info in pdf_infos:
        start_index = len(writer.pages)  # 이 파일이 시작되는 페이지 인덱스
        start_page_indices.append(start_index)
        for page in info["reader"].pages:
            writer.add_page(page)

    # 5. 북마크(Outline) 추가: 사이드바 북마크
    for info, page_index in zip(pdf_infos, start_page_indices):
        writer.add_outline_item(info["name"], page_index)

    # 6. 목차 페이지에 클릭 가능한 링크 추가
    #    Link(rect=..., target_page_index=...) 사용
    for i, (entry, y) in enumerate(zip(entries, link_positions)):
        target_page_index = start_page_indices[i]  # 이동할 페이지 (0-based)

        # 텍스트 줄 전체를 넉넉하게 감싸는 사각형 설정
        rect = (
            70,                  # xLL (왼쪽)
            y - 2,               # yLL (아래)
            toc_page_width - 70, # xUR (오른쪽)
            y + 12               # yUR (위)
        )

        annotation = Link(
            rect=rect,
            target_page_index=target_page_index,
        )

        # 0번 페이지(목차)에 주석 추가
        writer.add_annotation(page_number=0, annotation=annotation)

    # 7. 결과를 바이트로 반환
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.getvalue()


def main():
    st.title("PDF 병합 + 클릭 가능한 목차 생성 앱")
    st.write("여러 PDF를 업로드하면 하나로 병합하고, 첫 페이지에 목차를 만들어 줍니다.")
    st.write("목차에서 제목을 클릭하면 각 PDF의 첫 페이지로 바로 이동합니다.")

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

            st.success("병합이 완료되었습니다! (목차 클릭 시 해당 페이지로 이동)")
            st.download_button(
                label="병합된 PDF 다운로드",
                data=merged_pdf,
                file_name="merged_with_clickable_toc.pdf",
                mime="application/pdf",
            )


if __name__ == "__main__":
    main()
