#!/usr/bin/env python3
"""由 content.md 生成 Word 文档。

流程：生成样式模板 → 预处理（公式编号、结果填充）→ pandoc 转换（LaTeX 公式转为 Word 原生公式）
→ 后处理（公式右侧编号、三线表、页码、“式中”段落不缩进）。

运行：python3 docs/signal_param_estimation/src/build_docx.py
"""
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD = ROOT / "build"
OUT = ROOT / "信号源参数精确估计技术.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W_NS, "m": M_NS, "r": R_NS}
WDECL = f'xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:m="{M_NS}"'

TEXT_W = 11906 - 2 * 1418      # A4 宽度减左右页边距（twip）


def q(tag):
    p, t = tag.split(":")
    return f"{{{NS[p]}}}{t}"


def frag(xml):
    return etree.fromstring(f"<root {WDECL}>{xml}</root>")[0]


# ---------------------------------------------------------------- 样式
def fonts(east):
    return (f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
            f'w:eastAsia="{east}" w:cs="Times New Roman"/>')


SONG, HEI, KAI = fonts("宋体"), fonts("黑体"), fonts("楷体")


def pstyle(sid, name, based="Normal", ppr="", rpr="", nxt=None, custom=True, outline=None):
    c = ' w:customStyle="1"' if custom else ""
    n = f'<w:next w:val="{nxt}"/>' if nxt else ""
    o = f'<w:outlineLvl w:val="{outline}"/>' if outline is not None else ""
    return (f'<w:style w:type="paragraph"{c} w:styleId="{sid}"><w:name w:val="{name}"/>'
            f'<w:basedOn w:val="{based}"/>{n}<w:qFormat/><w:pPr>{ppr}{o}</w:pPr>'
            f'<w:rPr>{rpr}</w:rPr></w:style>')


STYLES = {
    "Normal": ('<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
               '<w:qFormat/><w:pPr><w:widowControl w:val="0"/><w:jc w:val="both"/></w:pPr>'
               f'<w:rPr>{SONG}<w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>'),
    "BodyText": pstyle("BodyText", "Body Text", custom=False,
                       ppr='<w:spacing w:before="0" w:after="0"/>'
                           '<w:ind w:firstLineChars="200" w:firstLine="420"/>'),
    "FirstParagraph": pstyle("FirstParagraph", "First Paragraph", "BodyText", nxt="BodyText"),
    "Compact": pstyle("Compact", "Compact",
                      ppr='<w:spacing w:before="24" w:after="24" w:line="240" w:lineRule="auto"/>'
                          '<w:jc w:val="center"/>',
                      rpr='<w:sz w:val="18"/><w:szCs w:val="18"/>'),
    "Title": pstyle("Title", "Title", custom=False, nxt="BodyText",
                    ppr='<w:keepNext/><w:spacing w:before="120" w:after="80" w:line="240" '
                        'w:lineRule="auto"/><w:jc w:val="center"/>',
                    rpr=f'{HEI}<w:b/><w:sz w:val="32"/><w:szCs w:val="32"/>'),
    "Subtitle": pstyle("Subtitle", "Subtitle", custom=False, nxt="BodyText",
                       ppr='<w:spacing w:before="0" w:after="240" w:line="240" w:lineRule="auto"/>'
                           '<w:jc w:val="center"/>',
                       rpr=f'{KAI}<w:sz w:val="24"/><w:szCs w:val="24"/>'),
    "Heading1": pstyle("Heading1", "heading 1", custom=False, nxt="BodyText", outline=0,
                       ppr='<w:keepNext/><w:keepLines/><w:spacing w:before="240" w:after="120"/>'
                           '<w:jc w:val="left"/>',
                       rpr=f'{HEI}<w:color w:val="000000"/><w:sz w:val="28"/><w:szCs w:val="28"/>'),
    "Heading2": pstyle("Heading2", "heading 2", custom=False, nxt="BodyText", outline=1,
                       ppr='<w:keepNext/><w:keepLines/><w:spacing w:before="120" w:after="60"/>'
                           '<w:jc w:val="left"/>',
                       rpr=f'{HEI}<w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/>'),
    "Heading3": pstyle("Heading3", "heading 3", custom=False, nxt="BodyText", outline=2,
                       ppr='<w:keepNext/><w:keepLines/><w:spacing w:before="120" w:after="60"/>',
                       rpr=f'{HEI}<w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/>'),
    "Caption": pstyle("Caption", "caption", custom=False,
                      ppr='<w:spacing w:before="60" w:after="120" w:line="240" w:lineRule="auto"/>'
                          '<w:jc w:val="center"/>',
                      rpr='<w:sz w:val="18"/><w:szCs w:val="18"/>'),
    "ImageCaption": pstyle("ImageCaption", "Image Caption", "Caption",
                           ppr='<w:spacing w:before="40" w:after="200"/>'),
    "TableCaption": pstyle("TableCaption", "Table Caption", "Caption",
                           ppr='<w:keepNext/><w:spacing w:before="160" w:after="60"/>'),
    "Figure": pstyle("Figure", "Figure",
                     ppr='<w:keepNext/><w:spacing w:before="120" w:after="0" w:line="240" '
                         'w:lineRule="auto"/><w:jc w:val="center"/>'),
    "CaptionedFigure": pstyle("CaptionedFigure", "Captioned Figure", "Figure",
                              ppr='<w:keepNext/>'),
}
EXTRA = [
    pstyle("TiYao", "提要",
           ppr='<w:spacing w:before="60" w:after="240" w:line="288" w:lineRule="auto"/>'
               '<w:ind w:left="420" w:right="420" w:firstLineChars="200" w:firstLine="360"/>',
           rpr=f'{KAI}<w:sz w:val="18"/><w:szCs w:val="18"/>'),
    pstyle("CanKao", "参考文献",
           ppr='<w:spacing w:before="0" w:after="40" w:line="276" w:lineRule="auto"/>'
               '<w:ind w:left="420" w:hanging="420"/>',
           rpr='<w:sz w:val="18"/><w:szCs w:val="18"/>'),
]

DOC_DEFAULTS = (f'<w:docDefaults><w:rPrDefault><w:rPr>{SONG}<w:sz w:val="21"/><w:szCs w:val="21"/>'
                '<w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
                '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="276" w:lineRule="auto"/>'
                '</w:pPr></w:pPrDefault></w:docDefaults>')

SECT = (f'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1418" w:right="1418" '
        f'w:bottom="1418" w:left="1418" w:header="851" w:footer="850" w:gutter="0"/>'
        f'<w:cols w:space="425"/></w:sectPr>')


def make_reference(dst):
    tmp = BUILD / "ref_src"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    default = BUILD / "ref_default.docx"
    subprocess.run(["pandoc", "-o", str(default), "--print-default-data-file", "reference.docx"],
                   check=True)
    with zipfile.ZipFile(default) as z:
        z.extractall(tmp)
    st_path = tmp / "word" / "styles.xml"
    tree = etree.parse(str(st_path))
    root = tree.getroot()
    old = root.find("w:docDefaults", NS)
    root.replace(old, frag(DOC_DEFAULTS))
    for sid, xml in STYLES.items():
        el = root.find(f'w:style[@w:styleId="{sid}"]', NS)
        new = frag(xml)
        if el is None:
            root.append(new)
        else:
            root.replace(el, new)
    for xml in EXTRA:
        root.append(frag(xml))
    tree.write(str(st_path), xml_declaration=True, encoding="UTF-8", standalone=True)
    doc_path = tmp / "word" / "document.xml"
    d = doc_path.read_text(encoding="utf-8")
    d = re.sub(r"<w:sectPr.*?</w:sectPr>", SECT, d, flags=re.S)
    doc_path.write_text(d, encoding="utf-8")
    zip_dir(tmp, dst)


def zip_dir(src, dst):
    if dst.exists():
        dst.unlink()
    files = sorted(p for p in src.rglob("*") if p.is_file())
    files.sort(key=lambda p: (p.name != "[Content_Types].xml", str(p)))
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(src).as_posix())


# ---------------------------------------------------------------- 预处理
def preprocess(md):
    eq = {}

    def num(m):
        eq[m.group(2)] = len(eq) + 1
        return f"$${m.group(1)}$$"

    md = re.sub(r"\$\$(.+?)\$\$\s*\{#eq:([\w-]+)\}", num, md, flags=re.S)
    assert "$$" not in re.sub(r"\$\$(.+?)\$\$", "", md, flags=re.S), "存在未编号的公式"
    n_display = len(re.findall(r"\$\$(.+?)\$\$", md, flags=re.S))
    assert n_display == len(eq), "所有行间公式都必须带编号标签"
    md = re.sub(r"\{\{eq:([\w-]+)\}\}", lambda m: str(eq[m.group(1)]), md)

    res = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    mods = {t["mod"]: t for t in res["modulation"]["table"]}

    def mod(m):
        t = mods[m.group(1)]
        k = m.group(2)
        return f"{t[k]:.2f}±{t[k + '_std']:.2f}".replace("-", "−")

    md = re.sub(r"\{\{mod:(\w+):(C4[02])\}\}", mod, md)
    assert "{{" not in md, re.findall(r"\{\{.*?\}\}", md)
    return md, len(eq)


# ---------------------------------------------------------------- 后处理
def number_equations(body):
    n = 0
    for p in list(body.iter(q("w:p"))):
        mp = p.find("m:oMathPara", NS)
        if mp is None:
            continue
        n += 1
        c1, c3 = 900, 900
        c2 = TEXT_W - c1 - c3
        tbl = frag(
            f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:jc w:val="center"/>'
            '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
            '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
            '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="0" w:type="dxa"/>'
            '<w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
            '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" '
            'w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="{c1}"/><w:gridCol w:w="{c2}"/><w:gridCol w:w="{c3}"/></w:tblGrid>'
            '<w:tr><w:trPr><w:cantSplit/></w:trPr>'
            f'<w:tc><w:tcPr><w:tcW w:w="{c1}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr></w:p></w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="{c2}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            '<w:p><w:pPr><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>'
            '<w:jc w:val="center"/></w:pPr></w:p></w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="{c3}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:jc w:val="right"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">({n})</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
        cell_p = tbl.findall(".//w:tc", NS)[1].find("w:p", NS)
        cell_p.append(mp)
        p.getparent().replace(p, tbl)
    return n


def three_line_tables(body):
    for tbl in body.findall("w:tbl", NS):
        tp = tbl.find("w:tblPr", NS)
        sty = tp.find("w:tblStyle", NS)
        if sty is None or sty.get(q("w:val")) != "Table":
            continue
        for tag in ("w:tblBorders", "w:jc", "w:tblW"):
            for e in tp.findall(tag, NS):
                tp.remove(e)
        tp.insert(1, frag(f'<w:tblW w:w="{TEXT_W}" w:type="dxa"/>'))
        tp.insert(2, frag('<w:jc w:val="center"/>'))
        tp.insert(3, frag('<w:tblBorders><w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
                          '<w:left w:val="nil"/><w:bottom w:val="single" w:sz="12" w:space="0" '
                          'w:color="000000"/><w:right w:val="nil"/><w:insideH w:val="nil"/>'
                          '<w:insideV w:val="nil"/></w:tblBorders>'))
        rows = tbl.findall("w:tr", NS)
        for tc in rows[0].findall("w:tc", NS):
            tcp = tc.find("w:tcPr", NS)
            if tcp is None:
                tcp = etree.SubElement(tc, q("w:tcPr"))
                tc.insert(0, tcp)
            tcp.append(frag('<w:tcBorders><w:bottom w:val="single" w:sz="6" w:space="0" '
                            'w:color="000000"/></w:tcBorders>'))
            for r in tc.iter(q("w:r")):
                rpr = r.find("w:rPr", NS)
                if rpr is None:
                    rpr = etree.Element(q("w:rPr"))
                    r.insert(0, rpr)
                rpr.insert(0, frag("<w:b/>"))
        for tr in rows[:-1]:
            for pp in tr.iter(q("w:p")):
                ppr = pp.find("w:pPr", NS)
                if ppr is None:
                    ppr = etree.Element(q("w:pPr"))
                    pp.insert(0, ppr)
                ppr.append(frag("<w:keepNext/>"))
        for tr in rows:
            trpr = tr.find("w:trPr", NS)
            if trpr is None:
                trpr = etree.Element(q("w:trPr"))
                tr.insert(0, trpr)
            trpr.append(frag("<w:cantSplit/>"))
            for tc in tr.findall("w:tc", NS):
                tcp = tc.find("w:tcPr", NS)
                if tcp is not None and tcp.find("w:vAlign", NS) is None:
                    tcp.append(frag('<w:vAlign w:val="center"/>'))


def no_indent_after_equations(body):
    for p in body.findall("w:p", NS):
        txt = "".join(t.text or "" for t in p.iter(q("w:t"))).lstrip()
        if txt.startswith(("式中", "其中")):
            ppr = p.find("w:pPr", NS)
            if ppr is None:
                ppr = etree.Element(q("w:pPr"))
                p.insert(0, ppr)
            ppr.append(frag('<w:ind w:firstLineChars="0" w:firstLine="0"/>'))


FOOTER = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {WDECL}>'
          '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
          '<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
          '<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
          '<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>'
          '<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t>1</w:t></w:r>'
          '<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')


def add_footer(unz, body):
    (unz / "word" / "footer1.xml").write_text(FOOTER, encoding="utf-8")
    rels = unz / "word" / "_rels" / "document.xml.rels"
    s = rels.read_text(encoding="utf-8")
    s = s.replace("</Relationships>",
                  '<Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/'
                  'officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>')
    rels.write_text(s, encoding="utf-8")
    ct = unz / "[Content_Types].xml"
    s = ct.read_text(encoding="utf-8")
    s = s.replace("</Types>", '<Override PartName="/word/footer1.xml" ContentType="application/'
                  'vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
    if 'Extension="png"' not in s:
        s = re.sub(r"(<Types[^>]*>)", r'\1<Default Extension="png" ContentType="image/png"/>', s, count=1)
    ct.write_text(s, encoding="utf-8")
    sect = body.find("w:sectPr", NS)
    sect.insert(0, frag('<w:footerReference w:type="default" r:id="rIdFooter1"/>'))


# ---------------------------------------------------------------- 规范化（修正 pandoc 输出的元素顺序）
ORDER = {
    "w:pPr": "pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers "
             "pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE "
             "autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents "
             "suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle "
             "rPr sectPr pPrChange",
    "w:rPr": "rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint "
             "noProof snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u "
             "effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath",
    "w:tcPr": "cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText "
              "vAlign hideMark headers cellIns cellDel cellMerge tcPrChange",
    "w:tblPr": "tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc "
               "tblCellSpacing tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription",
    "w:style": "name aliases basedOn next link autoRedefine hidden uiPriority semiHidden unhideWhenUsed "
               "qFormat locked personal personalCompose personalReply rsid pPr rPr tblPr trPr tcPr tblStylePr",
    "m:dPr": "begChr sepChr endChr grow shp ctrlPr",
    "m:rPr": "lit nor scr sty brk aln",
    "m:mcPr": "count mcJc",
}


def sanitize(root):
    for tag, order in ORDER.items():
        pre = tag.split(":")[0]
        rank = {q(f"{pre}:{n}"): i for i, n in enumerate(order.split())}
        for el in root.iter(q(tag)):
            if tag == "m:rPr" and el.find("m:nor", NS) is not None:
                for t in ("m:scr", "m:sty"):
                    for e in el.findall(t, NS):
                        el.remove(e)
            kids = list(el)
            if tag in ("w:rPr", "w:pPr", "w:tcPr", "w:tblPr"):
                el.text = None
                for k in kids:
                    k.tail = None
            kids.sort(key=lambda k: rank.get(k.tag, len(rank)))
            for k in kids:
                el.remove(k)
            for k in kids:
                el.append(k)


SETTINGS = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings {WDECL}>'
            '<w:zoom w:percent="100"/><w:proofState w:spelling="clean" w:grammar="clean"/>'
            '<w:defaultTabStop w:val="420"/><w:characterSpacingControl w:val="compressPunctuation"/>'
            '<w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'
            '<w:compat><w:compatSetting w:name="compatibilityMode" '
            'w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
            '<m:mathPr><m:mathFont m:val="Cambria Math"/><m:brkBin m:val="before"/>'
            '<m:brkBinSub m:val="--"/><m:smallFrac m:val="0"/><m:dispDef/><m:lMargin m:val="0"/>'
            '<m:rMargin m:val="0"/><m:defJc m:val="centerGroup"/><m:wrapIndent m:val="1440"/>'
            '<m:intLim m:val="subSup"/><m:naryLim m:val="undOvr"/></m:mathPr>'
            '<w:themeFontLang w:val="en-US" w:eastAsia="zh-CN"/>'
            '<w:decimalSymbol w:val="."/><w:listSeparator w:val=","/></w:settings>')


def sanitize_package(unz):
    for part in ("word/styles.xml", "word/document.xml"):
        path = unz / part
        tree = etree.parse(str(path))
        sanitize(tree.getroot())
        tree.write(str(path), xml_declaration=True, encoding="UTF-8", standalone=True)
    (unz / "word" / "settings.xml").write_text(SETTINGS, encoding="utf-8")
    num = unz / "word" / "numbering.xml"
    if num.exists():
        s = num.read_text(encoding="utf-8")
        s = re.sub(r'(<w:(?:nsid|tmpl) w:val=")([0-9A-Fa-f]{1,7})(")',
                   lambda m: m.group(1) + m.group(2).zfill(8) + m.group(3), s)
        num.write_text(s, encoding="utf-8")


def postprocess(raw, dst, n_eq):
    unz = BUILD / "out_src"
    shutil.rmtree(unz, ignore_errors=True)
    with zipfile.ZipFile(raw) as z:
        z.extractall(unz)
    doc_path = unz / "word" / "document.xml"
    tree = etree.parse(str(doc_path))
    body = tree.getroot().find("w:body", NS)
    n = number_equations(body)
    assert n == n_eq, (n, n_eq)
    three_line_tables(body)
    no_indent_after_equations(body)
    add_footer(unz, body)
    tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)
    sanitize_package(unz)
    zip_dir(unz, dst)


def main():
    BUILD.mkdir(exist_ok=True)
    ref = BUILD / "reference.docx"
    make_reference(ref)
    md, n_eq = preprocess((HERE / "content.md").read_text(encoding="utf-8"))
    pre = BUILD / "content_processed.md"
    pre.write_text(md, encoding="utf-8")
    raw = BUILD / "raw.docx"
    subprocess.run(["pandoc", str(pre), "-f", "markdown", "-t", "docx", "-o", str(raw),
                    "--reference-doc", str(ref), "--resource-path", str(ROOT)],
                   check=True, cwd=ROOT)
    postprocess(raw, OUT, n_eq)
    print(f"written {OUT} ({n_eq} equations)")


if __name__ == "__main__":
    main()
