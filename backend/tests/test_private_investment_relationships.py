"""Synthetic-only investment relationship registry; no real owner/partner names."""
import json
import pytest

from app.private_investment_relationships import (
    PrivateInvestmentRegistryBlocked,private_investment_relationships,
)


def fixture():
    return {
        "property_register_group_id":"property_group",
        "groups":[
            {"id":"property_group","title":"Synthetic Partner One",
             "ventures":[{"id":"real_estate","title":"Synthetic land venture",
                          "category":"property"}]},
            {"id":"multi_venture","title":"Synthetic Partner Two",
             "ventures":[{"id":"school_venture","title":"Synthetic school",
                          "category":"education"},
                         {"id":"book_venture","title":"Synthetic publisher",
                          "category":"business"}]},
        ],
    }


def test_owner_declaration_is_private_only_and_never_a_verified_cash_balance(monkeypatch):
    monkeypatch.setenv("P6B_PRIVATE_RELATIONSHIPS_JSON",json.dumps(fixture()))
    result=private_investment_relationships(property_verified=True)
    assert result["contract"]=="personal_cfo_p6_owner_investment_registry_v1"
    assert result["source"]=="PRIVATE_OWNER_DECLARATION"
    assert len(result["groups"])==2
    assert result["groups"][0]["ventures"][0]["evidence_status"]==(
        "PROPERTY_REGISTER_RECONCILED_HISTORICAL_COSTS_ONLY")
    assert result["groups"][0]["ventures"][0]["property_register_linked"] is True
    assert result["groups"][1]["ventures"][0]["property_register_linked"] is False
    assert result["groups"][1]["ventures"][1]["property_register_linked"] is False
    assert result["groups"][1]["ventures"][0]["confirmed_invested_principal_minor"] is None
    assert result["groups"][1]["ventures"][1]["current_market_value_minor"] is None
    assert result["groups"][1]["ventures"][1]["realized_cash_return_minor"] is None
    assert result["current_market_values_verified"] is False
    assert result["all_investment_contributions_reconciled"] is False


def test_unavailable_workbook_does_not_promote_owner_declaration_to_verified(monkeypatch):
    monkeypatch.setenv("P6B_PRIVATE_RELATIONSHIPS_JSON",json.dumps(fixture()))
    result=private_investment_relationships(property_verified=False)
    assert all(not v["property_register_linked"] for g in result["groups"]
               for v in g["ventures"])
    assert all(v["evidence_status"]=="OWNER_DECLARED_AWAITING_TRANSACTION_ALLOCATION"
               for g in result["groups"] for v in g["ventures"])


def test_default_empty_private_config_is_safe(monkeypatch):
    monkeypatch.delenv("P6B_PRIVATE_RELATIONSHIPS_JSON",raising=False)
    result=private_investment_relationships(property_verified=True)
    assert result["groups"]==[]
    assert result["property_register_group_id"] is None


@pytest.mark.parametrize("mutate",[
    lambda o:o.update(property_register_group_id="missing_group"),
    lambda o:o["groups"][1].update(id="property_group"),
    lambda o:o["groups"][1]["ventures"][0].update(id="book_venture"),
    lambda o:o["groups"][0]["ventures"][0].update(category="fictional_currency"),
    lambda o:o["groups"][0]["ventures"][0].update(confirmed_invested_principal_minor=100),
    lambda o:o["groups"][0].update(title="Fake\\nheader"),
    lambda o:o.update(groups=[]),
    lambda o:o["groups"][0]["ventures"].append({
        "id":"second_property","title":"Unreconciled property","category":"property"}),
])
def test_malformed_owner_context_fails_closed(monkeypatch,mutate):
    data=fixture()
    mutate(data)
    monkeypatch.setenv("P6B_PRIVATE_RELATIONSHIPS_JSON",json.dumps(data))
    with pytest.raises(PrivateInvestmentRegistryBlocked):
        private_investment_relationships(property_verified=True)


def test_duplicate_keys_fail_closed(monkeypatch):
    valid=json.dumps(fixture())
    tampered=valid.replace('"property_register_group_id":','"property_register_group_id":"other", "property_register_group_id":',1)
    monkeypatch.setenv("P6B_PRIVATE_RELATIONSHIPS_JSON",tampered)
    with pytest.raises(PrivateInvestmentRegistryBlocked):
        private_investment_relationships(property_verified=True)


def test_oversized_private_setting_not_parsed(monkeypatch):
    monkeypatch.setenv("P6B_PRIVATE_RELATIONSHIPS_JSON","x"*4097)
    with pytest.raises(PrivateInvestmentRegistryBlocked):
        private_investment_relationships(property_verified=True)
