"""Synthetic-only strict XLSX investment cost/profit reconciliation tests."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import pytest
from app.private_property_inventory_reconciler import (
    reconcile_property_inventory_xlsx,PrivatePropertyRegisterBlocked)
from app.private_owner_property_inventory_report import (
    PrivatePropertyInventoryReportBlocked,get_private_property_inventory_overview)
from xml.sax.saxutils import escape

def fabricated_inventory():
    strings=["Inventories Purchase/Sales for Example Sb","Ser. #","Buying","Selling",
             "Plot/Shop","Available Investment","Total Profit Earned Yet",
             "60% Example","40% Example"]+[f"Asset {n+1}" for n in range(12)]
    def c(addr,val,string=False):
        typ=' t="s"' if string else ''
        encoded=strings.index(val) if string else val
        return f'<c r="{addr}"{typ}><v>{encoded}</v></c>'
    cells=[c("A1",strings[0],True),c("A2","Ser. #",True),
        c("B2","Buying",True),c("D2","Selling",True),
        c("B125","Available Investment",True),
        c("C125","Total Profit Earned Yet",True),
        c("D125","60% Example",True),c("E125","40% Example",True)]
    held=profits=owner_share=other_share=0
    for n in range(12):
        row=3+n*10
        sold=n in (0,1,2,3,8,9)
        cells += [c(f"A{row}",n+1),c(f"B{row}","Plot/Shop",True),
                  c(f"C{row}",f"Asset {n+1}",True),
                  c(f"C{row+1}",46000),c(f"C{row+2}",100),
                  c(f"C{row+3}",0),c(f"C{row+4}",0),c(f"C{row+5}",0),
                  c(f"E{row+3}",0),c(f"E{row+4}",0),c(f"E{row+5}",0),
                  c(f"C{row+6}",100)]
        if sold:
            cells += [c(f"E{row+1}",46100),c(f"E{row+2}",110),c(f"E{row+6}",110),
                      c(f"C{row+7}",10),c(f"C{row+8}",6),
                      c(f"C{row+9}",4)]
            profits+=10;owner_share+=6;other_share+=4
        else:
            cells += [c(f"E{row+2}",0),c(f"E{row+6}",0),c(f"C{row+7}",0),
                      c(f"C{row+8}",0),c(f"C{row+9}",0)]
            held+=100
    cells += [c("B126",held),c("C126",profits),
              c("D126",owner_share),c("E126",other_share)]
    xml='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(cells)+'</sheetData></worksheet>'
    shared='<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+''.join(
      '<si><t>'+escape(s)+'</t></si>' for s in strings)+'</sst>'
    output=BytesIO()
    with ZipFile(output,"w",ZIP_DEFLATED) as zipfile:
        for name,payload in (
            ("[Content_Types].xml","<Types/>"),
            ("xl/workbook.xml","<workbook/>"),
            ("xl/sharedStrings.xml",shared),
            ("xl/worksheets/sheet1.xml",xml),
        ):
            zipfile.writestr(name,payload)
    return output.getvalue()

def test_register_recovers_cost_profit_shares_not_market_value():
    record=reconcile_property_inventory_xlsx(fabricated_inventory())
    assert record["contract"]=="personal_cfo_p6_property_inventory_v1"
    assert record["property_count"]==12
    assert record["sold_property_count"]==6
    assert record["held_property_count"]==6
    assert record["held_recorded_investment_cost_minor"]==60000
    assert record["all_recorded_sale_profit_minor"]==6000
    assert record["owner_recorded_sale_profit_share_minor"]==3600
    assert record["other_party_recorded_share_minor"]==2400
    assert record["market_value_minor"] is None
    assert record["owner_total_net_worth_minor"] is None
    assert record["cash_proceeds_verified"] is False
    assert record["original_source_modified"] is False
    assert len(record["properties"])==12

@pytest.mark.parametrize("bad",[
    b"",b"not an XLSX",b"\x00"*200,(b"a"*4*1024*1024)+b"b"
])
def test_fails_closed_on_corrupted_xlsx(bad):
    with pytest.raises(PrivatePropertyRegisterBlocked):
        reconcile_property_inventory_xlsx(bad)

def test_bad_cached_summary_is_rejected_without_fabricating_holdings():
    blob=fabricated_inventory()
    inp=BytesIO(blob)
    out=BytesIO()
    with ZipFile(inp) as src, ZipFile(out,"w",ZIP_DEFLATED) as target:
        for filename in src.namelist():
            body=src.read(filename)
            if filename=="xl/worksheets/sheet1.xml":
                body=body.replace(b'<c r="B126"><v>600</v>',b'<c r="B126"><v>601</v>')
            target.writestr(filename,body)
    with pytest.raises(PrivatePropertyRegisterBlocked):
        reconcile_property_inventory_xlsx(out.getvalue())

def test_default_off_without_explicit_owner_gates(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF","fictional-owner-1234567890")
    monkeypatch.delenv("P6B_OWNER_INVESTMENT_RUNTIME",raising=False)
    with pytest.raises(PrivatePropertyInventoryReportBlocked):
        get_private_property_inventory_overview(
            session_factory=lambda:None,owner_ref="fictional-owner-1234567890")
