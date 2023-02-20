import os
from lxml import etree
from hashlib import sha1
from typing import Any, Optional
from copy import deepcopy
from dataclasses import dataclass

from common import WORKING_DIR_PATH
from common import Link

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"
etree.register_namespace("w", W_NS)
etree.register_namespace("r", R_NS)
etree.register_namespace("xml", XML_NS)

R_EMBED = etree.QName(R_NS, "embed")


DOCX_CONTENT_PATH = os.path.join(WORKING_DIR_PATH, "word/")
DOCUMENT_PATH = os.path.join(DOCX_CONTENT_PATH, "document.xml")
FOOTER_PATH = os.path.join(DOCX_CONTENT_PATH, "footer1.xml")
RELS_PATH = os.path.join(DOCX_CONTENT_PATH, "_rels/document.xml.rels")
MEDIA_PATH = os.path.join(DOCX_CONTENT_PATH, "media/")
REPORT_FILE_PATH = "./report.docx"

@dataclass
class Text:
    text: str
    bold: bool
    hex_color: str


def find_by_id(tree: etree.Element, id: str):
    return tree.find("//*[@id='{id}']".format(id=id))


def create_page_break():
    # <w:br w:type="page"/>
    return etree.Element(etree.QName(W_NS, "br"), {etree.QName(W_NS, "type"): "page"})


def create_whitespace() -> etree.Element:
    r = etree.Element(etree.QName(W_NS, "r"))
    etree.SubElement(
        r, etree.QName(W_NS, "t"), {etree.QName(XML_NS, "space"): "preserve"}
    ).text = " "

    return r


def create_paragraph():
    return etree.Element(etree.QName(W_NS, "p"))


def load_xml(file_path: str):
    tree = None
    with open(file_path, "r") as file:
        tree = etree.parse(file)

    return tree


def write_xml(tree, file_path: str):
    tree.write(file_path)


def create_relationship(url: str):
    # load rels file
    tree = load_xml(RELS_PATH)

    rels = tree.getroot()

    # generate uniq id for relationship
    rel_id = "rId" + sha1(bytearray(map(ord, url))).digest().hex()

    # add relationship element to xml

    etree.SubElement(
        rels,
        "Relationship",
        {
            "Id": rel_id,
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            "Target": url,
            "TargetMode": "External",
        },
    )

    # save resulting xml
    write_xml(tree, RELS_PATH)

    return rel_id


def remove_element(el: etree.Element):
    el.getparent().remove(el)


def update_relationship_target(rel_id: str, url: str):
    # load rels file
    tree = load_xml(RELS_PATH)

    rel = tree.find("//*[@Id='{id}']".format(id=rel_id))

    rel.attrib["Target"] = url

    # save resulting xml
    write_xml(tree, RELS_PATH)


def find_relationship(rel_id):
    # load rels file
    tree = load_xml(RELS_PATH)

    return tree.find("//*[@Id='{id}']".format(id=rel_id))


def get_image_file_location(image: etree.Element):
    rel_id = image.find(".//{*}blip").get(R_EMBED)

    rel = find_relationship(rel_id)

    image_path = rel.get("Target")
    return os.path.join(DOCX_CONTENT_PATH, image_path)


def create_hyperlink(link: Link):
    #     <w:hyperlink w:id="rID123">
    #       <w:r>
    #         <w:rPr>
    #           <w:rStyle w:val="ab"/>
    #         </w:rPr>
    #         <w:t>Description</w:t>
    #       </w:r>
    #     </w:hyperlink>

    # create external link relationship
    rel_id = create_relationship(link.url)

    hyperlink = etree.Element(
        etree.QName(W_NS, "hyperlink"),
        {etree.QName(R_NS, "id"): rel_id},
    )
    record = etree.SubElement(hyperlink, etree.QName(W_NS, "r"))

    # apply link style
    formatting = etree.SubElement(record, etree.QName(W_NS, "rPr"))
    etree.SubElement(
        formatting, etree.QName(W_NS, "rStyle"), {etree.QName(W_NS, "val"): "ab"}
    )

    # add link description
    text_field = etree.SubElement(record, etree.QName(W_NS, "t"))
    text_field.text = link.text

    return hyperlink


def append_content(paragraph, content: Any):
    if isinstance(content, list) or isinstance(content, tuple):
        for c in content:
            append_content(paragraph, c)

    elif isinstance(content, etree._Element):
        paragraph.append(content)

    elif isinstance(content, Text):
        # add custom text record inside paragraph
        record = create_text_record(text=content.text, bold=content.bold, hex_color=content.hex_color)
        paragraph.append(record)

    elif isinstance(content, Link):
        # add link record inside paragraph
        hyperlink = create_hyperlink(content)
        paragraph.append(hyperlink)

    elif isinstance(content, str):
        # add text record inside paragraph
        record = create_text_record(content)
        paragraph.append(record)


def create_text_record(text: str, bold: bool = False, hex_color: str = None):
    record = etree.Element(etree.QName(W_NS, "r"))
    style = etree.SubElement(record, etree.QName(W_NS, "rPr"))

    if bold:
        etree.SubElement(style, etree.QName(W_NS, "b"))
        etree.SubElement(style, etree.QName(W_NS, "bCs"))

    if hex_color is not None:
        etree.SubElement(style, etree.QName(W_NS, "color"), {etree.QName(W_NS, "val"): hex_color})

    text_field = etree.SubElement(record, etree.QName(W_NS, "t"))
    text_field.text = text

    return record


def create_bullet(list_id: int, lvl: int, content: Any):
    # create bullet element
    # <w:p>
    # <w:pPr>
    #     <w:pStyle w:val="a9" />
    #     <w:numPr>
    #       <w:ilvl w:val="0" />
    #       <w:numId w:val="0" />
    #     </w:numPr>
    # </w:pPr>
    # <w:r>
    #     <w:t>Text</w:t>
    # </w:r>
    # </w:p>
    paragraph = etree.Element(etree.QName(W_NS, "p"))
    style = etree.SubElement(paragraph, etree.QName(W_NS, "pPr"))

    etree.SubElement(
        style, etree.QName(W_NS, "pStyle"), {etree.QName(W_NS, "val"): "a9"}
    )

    numPr = etree.SubElement(style, etree.QName(W_NS, "numPr"))

    # list level
    etree.SubElement(
        numPr, etree.QName(W_NS, "ilvl"), {etree.QName(W_NS, "val"): str(lvl)}
    )

    # mark of list (to identify sequential numbers)
    etree.SubElement(
        numPr, etree.QName(W_NS, "numId"), {etree.QName(W_NS, "val"): str(list_id)}
    )

    append_content(paragraph, content)

    return paragraph


def append_element_after(new_el: etree.Element, after: etree.Element):
    parent = after.getparent()
    parent.insert(parent.index(after) + 1, new_el)


def append_element_before(new_el: etree.Element, before: etree.Element):
    parent = before.getparent()
    parent.insert(parent.index(before), new_el)


def update_link(tree: etree.Element, link_id: str, url: str, text: str):
    link = find_by_id(tree, link_id)

    # update link text
    bugs_desc = link.find(".//{*}t")
    bugs_desc.text = text

    # update link address
    rel_id = link.find("./{*}hyperlink").get(etree.QName(R_NS, "id"))
    update_relationship_target(rel_id, url)


def adjust_image_size(image_el: etree.Element, image_height: int, image_width: int):
    extent = image_el.find(".//{*}xfrm/{*}ext")
    image_doc_width = int(extent.get("cx"))

    extent.attrib["cy"] = str(int(image_doc_width * (image_height / image_width)))


def set_table_cell_value(cell: etree.Element, content: Any):
    # find paragraph inside the cell
    paragraph = cell.find("./{*}p")
    if paragraph is None:
        paragraph = etree.SubElement(cell, etree.QName(W_NS, "p"))

    append_content(paragraph, content)


def clear_table_cell(cell: etree.Element):
    # find paragraph inside the cell
    paragraph = cell.find("./{*}p")
    
    # remove all subelements except style tag
    for element in paragraph:
        if element.tag != etree.QName(W_NS, "pPr"):
            remove_element(element)


def table_add_rows(table: etree.Element, count: int):
    # find last row in the table
    last_row = table.find("./{*}tr[last()]")

    # and copy it specified amount of times
    for _ in range(count):
        table.append(deepcopy(last_row))
