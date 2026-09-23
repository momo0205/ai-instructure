"""提取三篇论文全文文本，并把含图（位图或大量矢量绘制）的页整页渲染为 PNG。

Run: python3 extract_papers.py
输出:
  papers/<name>/fulltext.txt      全文纯文本（翻译源）
  papers/<name>/figures/page_N.png 含图页的整页高清渲染
"""
import os
import pymupdf

BASE = os.path.dirname(os.path.abspath(__file__))

PAPERS = {
    "resnet": "papers/resnet/resnet.pdf",
    "transformer": "papers/transformer/attention_is_all_you_need.pdf",
    "ddpm": "papers/ddpm/ddpm.pdf",
}

# 矢量图判定阈值：一页矢量绘制数超过此值认为该页含图
VECTOR_THRESHOLD = 30


def extract(name, rel_pdf):
    pdf = os.path.join(BASE, rel_pdf)
    doc = pymupdf.open(pdf)
    figdir = os.path.join(BASE, "papers", name, "figures")
    os.makedirs(figdir, exist_ok=True)

    full_text = []
    fig_pages = []
    for i in range(len(doc)):
        page = doc[i]
        full_text.append(f"\n\n===== PAGE {i+1} =====\n")
        full_text.append(page.get_text())

        n_bitmap = len(page.get_images())
        n_vector = len(page.get_drawings())
        if n_bitmap > 0 or n_vector >= VECTOR_THRESHOLD:
            fig_pages.append((i, n_bitmap, n_vector))
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
            out = os.path.join(figdir, f"page_{i}.png")
            pix.save(out)

    txt_path = os.path.join(BASE, "papers", name, "fulltext.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("".join(full_text))

    doc.close()
    print(f"[{name}] {len(full_text)//2}页, 文本 {os.path.getsize(txt_path)//1024}KB, 含图页 {len(fig_pages)} 页:")
    for (i, nb, nv) in fig_pages:
        print(f"    page {i+1}: bitmap={nb} vector={nv}")


if __name__ == "__main__":
    for name, rel in PAPERS.items():
        extract(name, rel)
