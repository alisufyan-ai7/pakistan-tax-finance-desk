"""Strict, bounded evidence extraction for a privately pinned property register XLSX.

Only trusted private callers provide complete SHA-verified bytes. Untrusted OOXML
is never executed; zip member counts, sizes, compression ratios, formulas, cached
amounts and the row format are checked before any financial observation. These
values are recorded property costs and sale profits, NOT market valuations.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile, BadZipFile

NS="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_MAX_FILE=4*1024*1024
_MAX_EXPANDED=3*1024*1024
_NAMES=frozenset(("[Content_Types].xml","_rels/.rels",
    "xl/_rels/workbook.xml.rels","xl/workbook.xml","xl/sharedStrings.xml",
    "xl/worksheets/_rels/sheet1.xml.rels","xl/theme/theme1.xml",
    "xl/styles.xml","xl/worksheets/sheet1.xml","xl/calcChain.xml",
    "xl/printerSettings/printerSettings1.bin","docProps/core.xml",
    "docProps/app.xml"))
_A1=re.compile(r"^[A-G](?:[1-9]|[1-9][0-9]|1(?:0[0-9]|1[0-9]|2[0-6]))$")
_ASSET=re.compile(r"^[\w /.,()+&-]{1,100}$",re.UNICODE)
_MAX_MONEY=10**10


class PrivatePropertyRegisterBlocked(ValueError):
    """Owner property register unsupported or requires human reconciliation."""


def _whole(value: str) -> int:
    if not isinstance(value,str) or len(value)>35:
        raise ValueError()
    d=Decimal(value)
    if not d.is_finite() or d!=d.to_integral_value() or not 0<=d<=_MAX_MONEY:
        raise ValueError()
    return int(d)


def _date_serial(value: str) -> str:
    serial=_whole(value)
    if not 43000<=serial<=60000:
        raise ValueError()
    return (date(1899,12,30)+timedelta(days=serial)).isoformat()


def reconcile_property_inventory_xlsx(data: bytes) -> dict:
    if type(data) is not bytes or not 0<len(data)<=_MAX_FILE:
        raise PrivatePropertyRegisterBlocked("Property register source unavailable")
    try:
        with ZipFile(BytesIO(data)) as z:
            infos=z.infolist()
            if (not 4<=len(infos)<=30
                or any(i.filename not in _NAMES or i.flag_bits&1 or i.file_size>_MAX_EXPANDED
                       or i.compress_size<1 or i.file_size>max(1500,i.compress_size*80)
                       for i in infos)
                or len({i.filename for i in infos})!=len(infos)
                or sum(i.file_size for i in infos)>_MAX_EXPANDED):
                raise ValueError()
            required=("xl/workbook.xml","xl/sharedStrings.xml",
                      "xl/worksheets/sheet1.xml")
            if any(f not in z.namelist() for f in required):
                raise ValueError()
            workbook=z.read(required[0])
            if b"externalReference" in workbook or b"\x00" in workbook:
                raise ValueError()
            shared=z.read(required[1])
            sheet=z.read(required[2])
            if any(b"<!DOCTYPE" in x or b"<!ENTITY" in x for x in (workbook,shared,sheet)):
                raise ValueError()
        root=ET.fromstring(sheet)
        strings=ET.fromstring(shared)
        label_list=["".join((node.text or "") for node in si.iter(NS+"t"))
                    for si in strings.findall(NS+"si")]
        if len(label_list)>600 or any(len(x)>500 for x in label_list):
            raise ValueError()
        cells={}
        for cell in root.iter(NS+"c"):
            key=cell.get("r","")
            if not _A1.fullmatch(key) or key in cells:
                raise ValueError()
            raw=cell.findtext(NS+"v")
            formula=cell.findtext(NS+"f")
            if cell.get("t")=="e":
                raise ValueError()
            if formula and (len(formula)>180 or any(ch in formula for ch in "[]!")):
                raise ValueError()
            if cell.get("t")=="s":
                if raw is None or not raw.isdecimal() or int(raw)>=len(label_list):
                    raise ValueError()
                value=label_list[int(raw)]
            elif cell.get("t") in (None,"n"):
                value=raw
            else:
                raise ValueError()
            cells[key]=(value,formula)
        def value(key):
            return cells.get(key,(None,None))[0]
        if (value("A1")!="Inventories Purchase/Sales for Ali Sufyan Sb"
            or value("A2")!="Ser. #" or value("B2")!="Buying"
            or value("D2")!="Selling" or value("B125")!="Available Investment"
            or value("C125")!="Total Profit Earned Yet"
            or value("D125")!="60% Ali Sufyan Sb"
            or value("E125")!="40% Shahid Swati"):
            raise ValueError()
        assets=[]
        held_cost=profit_all=profit_owner=profit_partner=0
        last_sale=""
        for n in range(12):
            start=3+10*n
            if _whole(value(f"A{start}"))!=n+1 or value(f"B{start}")!="Plot/Shop":
                raise ValueError()
            label=value(f"C{start}")
            if type(label) is not str or not _ASSET.fullmatch(label):
                raise ValueError()
            purchased=_date_serial(value(f"C{start+1}"))
            sale_date=value(f"E{start+1}")
            bought=_whole(value(f"C{start+6}"))
            sold=_whole(value(f"E{start+6}"))
            gross_profit=_whole(value(f"C{start+7}"))
            owner=_whole(value(f"C{start+8}"))
            partner=_whole(value(f"C{start+9}"))
            if sold:
                if sale_date is None or _date_serial(sale_date)<purchased:
                    raise ValueError()
                dt=_date_serial(sale_date)
                if sold < bought or gross_profit!=sold-bought or owner+partner!=gross_profit:
                    raise ValueError()
                if owner*5!=gross_profit*3 or partner*5!=gross_profit*2:
                    raise ValueError()
                last_sale=max(last_sale,dt)
                profit_all+=gross_profit
                profit_owner+=owner
                profit_partner+=partner
                state="SOLD_IN_SOURCE_REGISTER"
            else:
                if sale_date is not None or any(x!=0 for x in (gross_profit,owner,partner)):
                    raise ValueError()
                dt=None
                held_cost+=bought
                state="HELD_COST_NOT_MARKET_VALUE"
            assets.append({"ordinal":n+1,"property_label":label,"purchase_date":purchased,
                           "sale_date":dt,"source_status":state,
                           "recorded_purchase_cost_minor":bought*100,
                           "net_sale_proceeds_minor":sold*100 if sold else None,
                           "recorded_profit_minor":gross_profit*100 if sold else None,
                           "recorded_owner_profit_share_minor":owner*100 if sold else None})
        if (_whole(value("B126"))!=held_cost
            or _whole(value("C126"))!=profit_all
            or _whole(value("D126"))!=profit_owner
            or _whole(value("E126"))!=profit_partner
            or profit_owner+profit_partner!=profit_all):
            raise ValueError()
        return {
            "contract":"personal_cfo_p6_property_inventory_v1",
            "source_type":"PROPERTY_COST_AND_SALES_REGISTER",
            "property_count":len(assets),
            "held_property_count":sum(a["source_status"]=="HELD_COST_NOT_MARKET_VALUE" for a in assets),
            "sold_property_count":sum(a["source_status"]=="SOLD_IN_SOURCE_REGISTER" for a in assets),
            "held_recorded_investment_cost_minor":held_cost*100,
            "all_recorded_sale_profit_minor":profit_all*100,
            "owner_recorded_sale_profit_share_minor":profit_owner*100,
            "other_party_recorded_share_minor":profit_partner*100,
            "latest_sale_date":last_sale,
            "properties":assets,
            "market_value_minor":None,
            "owner_total_net_worth_minor":None,
            "cash_proceeds_verified":False,
            "original_source_modified":False,
            "owner_review_required":True,
        }
    except (ValueError,KeyError,TypeError,BadZipFile,ET.ParseError,
            OverflowError,InvalidOperation):
        raise PrivatePropertyRegisterBlocked(
            "Property workbook layout, formulas or figures require owner review"
        ) from None
