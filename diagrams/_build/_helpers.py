"""draw.io helpers (from milliman-panel-notes diagrams/_build): boxes, groups, edges, Databricks icons."""
from pathlib import Path
from xml.sax.saxutils import escape as _escape


def escape(t):
    return _escape(t, {'"': "&quot;"})

# AWS icon colours by service category (the AWS architecture icon palette)
STORAGE, APP_INT, SECURITY, NETWORK, COMPUTE, MGMT, ANALYTICS, DB, MIGRATION = (
    "#7AA116", "#E7157B", "#DD344C", "#8C4FFF", "#ED7100", "#E7157B", "#8C4FFF", "#C925D1", "#01A88D")
DBX = "#FF3621"   # databricks

cells = []
_n = [0]


def nid():
    _n[0] += 1
    return f"c{_n[0]}"


def reset():
    cells.clear(); _n[0] = 0
    cells.append('<mxCell id="0"/><mxCell id="1" parent="0"/>')


def title(text, x=40, y=10, w=1500):
    cells.append(f'<mxCell id="{nid()}" value="{escape(text)}" style="text;html=1;fontSize=20;fontStyle=1;align=left;verticalAlign=middle;" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="40" as="geometry"/></mxCell>')


def note(text, x, y, w=1500, h=40):
    cells.append(f'<mxCell id="{nid()}" value="{escape(text)}" style="text;html=1;fontSize=12;align=left;verticalAlign=top;whiteSpace=wrap;fontColor=#545B64;" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def group(cid, label, kind, x, y, w, h):
    styles = {
        "cloud":  "grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;",
        "vpc":    "grIcon=mxgraph.aws4.group_vpc;strokeColor=#8C4FFF;fillColor=none;",
        "private": "grIcon=mxgraph.aws4.group_security_group;strokeColor=#00A4A6;fillColor=#E6F6F7;",
        "public": "grIcon=mxgraph.aws4.group_security_group;strokeColor=#7AA116;fillColor=#F2F6E8;",
        "dbx":    "grIcon=mxgraph.aws4.group_corporate_data_center;strokeColor=#FF3621;fillColor=none;",
        "ext":    "grIcon=mxgraph.aws4.group_corporate_data_center;strokeColor=#7D8998;fillColor=none;dashed=1;",
        "plain":  "strokeColor=#7D8998;fillColor=none;dashed=1;",
        "onprem": "grIcon=mxgraph.aws4.group_corporate_data_center;strokeColor=#232F3E;fillColor=none;",
        "az":     "grIcon=mxgraph.aws4.group_availability_zone;strokeColor=#147EBA;fillColor=none;dashed=1;",
        "subnet_private": "grIcon=mxgraph.aws4.group_security_group;strokeColor=#147EBA;fillColor=#E6F2F8;",
        "subnet_public":  "grIcon=mxgraph.aws4.group_security_group;strokeColor=#7AA116;fillColor=#F2F6E8;",
        "sg":     "grIcon=mxgraph.aws4.group_security_group;strokeColor=#DD344C;fillColor=none;",
        "dbxctl": "grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#FF3621;fillColor=#FFF7F5;",
        "saas":   "grIcon=mxgraph.aws4.group_corporate_data_center;strokeColor=#0073FF;fillColor=none;dashed=1;",
        "dbxlake": "strokeColor=#FF3621;fillColor=#FFF7F5;",
    }
    style = ("points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];"
             "outlineConnect=0;gradientColor=none;dashed=0;verticalAlign=top;align=left;spacingLeft=30;fontStyle=1;fontColor=#232F3E;"
             "html=1;whiteSpace=wrap;shape=mxgraph.aws4.group;fontSize=13;" + styles[kind])
    if kind in ("plain", "dbxlake"):
        style = "rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;align=left;spacingLeft=8;fontStyle=1;fontColor=#232F3E;fontSize=13;" + styles[kind]
    cells.append(f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def icon(cid, label, res, color, x, y, size=64):
    style = ("sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;"
             f"align=center;html=1;fontSize=11;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};"
             f"fillColor={color};strokeColor=#ffffff;")
    cells.append(f'<mxCell id="{cid}" value="{escape(label).replace(chr(10), "&lt;br&gt;")}" style="{style}" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>')


import base64
ICON_DIR = Path(__file__).parent / "dbx_icons"


def dbx_icon(cid, label, slug, x, y, size=56):
    """A Databricks product icon (oieduardorabelo/databricks-architecture-icons, Apache-2.0), embedded so the file is self-contained."""
    svg = base64.b64encode((ICON_DIR / f"{slug}.svg").read_bytes()).decode()
    style = (f"shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;html=1;fontSize=11;fontColor=#232F3E;"
             f"image=data:image/svg+xml,{svg};")
    cells.append(f'<mxCell id="{cid}" value="{escape(label).replace(chr(10), "&lt;br&gt;")}" style="{style}" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>')


def lane(label, x, y, w, h=34):
    cells.append(f'<mxCell id="{nid()}" value="{escape(label)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#EAEDED;strokeColor=none;fontSize=15;fontStyle=1;fontColor=#232F3E;" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def box(cid, label, x, y, w, h, color=DBX, fill="#FFF3F0"):
    style = f"rounded=1;whiteSpace=wrap;html=1;fontSize=11;fontColor=#232F3E;strokeColor={color};strokeWidth=2;fillColor={fill};"
    cells.append(f'<mxCell id="{cid}" value="{escape(label).replace(chr(10), "&lt;br&gt;")}" style="{style}" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def edge(src, dst, label="", dashed=False, exit=None, entry=None, via=()):
    pts = ""
    if exit: pts += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
    if entry: pts += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
    style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeColor=#545B64;"
             f"strokeWidth=1.5;fontSize=10;fontColor=#232F3E;labelBackgroundColor=#ffffff;{'dashed=1;' if dashed else ''}{pts}")
    geo = '<mxGeometry relative="1" as="geometry">' + ('<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in via) + '</Array>' if via else '') + '</mxGeometry>'
    cells.append(f'<mxCell id="{nid()}" value="{escape(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">{geo}</mxCell>')



def save(name, page_w=1600, page_h=900):
    xml = (f'<mxfile host="app.diagrams.net" agent="health-transformation-lab-nlp build_drawio.py"><diagram name="{name}"><mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" '
           f'guides="1" page="1" pageScale="1" pageWidth="{page_w}" pageHeight="{page_h}" background="#ffffff"><root>' + "".join(cells) + '</root></mxGraphModel></diagram></mxfile>')
    out = Path(__file__).parent.parent / f"{name}.drawio"
    out.write_text(xml)
    print(name)


def entity(cid, name, fields, x, y, w=230, color="#147EBA", fill="#E6F2F8"):
    """ERD table: header + one row per field ('PK id', 'FK person_id', 'name')."""
    row_h, head_h = 22, 30
    h = head_h + row_h * len(fields)
    cells.append(f'<mxCell id="{cid}" value="{escape(name)}" style="swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize={head_h};'
                 f'horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;html=1;fontSize=12;'
                 f'strokeColor={color};fillColor={fill};rounded=0;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    for i, fld in enumerate(fields):
        bold = "fontStyle=1;" if fld.startswith("PK") else ("fontStyle=2;" if fld.startswith("FK") else "")
        cells.append(f'<mxCell id="{cid}_f{i}" value="{escape(fld)}" style="text;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;'
                     f'spacingLeft=6;html=1;fontSize=11;{bold}" vertex="1" parent="{cid}"><mxGeometry y="{head_h + i * row_h}" width="{w}" height="{row_h}" as="geometry"/></mxCell>')
    return h


def rel(src, dst, label="", dashed=False, exit=None, entry=None, via=()):
    """ERD relationship, many-to-one (crow's foot at the many end), routed orthogonally."""
    pts = ""
    if exit: pts += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
    if entry: pts += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
    style = ("edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;fontSize=10;html=1;endArrow=ERmandOne;startArrow=ERmany;"
             f"endFill=0;startFill=0;strokeColor=#545B64;strokeWidth=1.2;labelBackgroundColor=#ffffff;{'dashed=1;' if dashed else ''}{pts}")
    geo = '<mxGeometry relative="1" as="geometry">' + ('<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in via) + '</Array>' if via else '') + '</mxGeometry>'
    cells.append(f'<mxCell id="{nid()}" value="{escape(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">{geo}</mxCell>')
