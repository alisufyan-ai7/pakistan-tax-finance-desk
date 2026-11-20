"""Bounded *private Railway setting* for owner-declared investment relationships.

Partner names / venture names live ONLY in the already secured owner's Railway
environment, never in the public repository or browser storage. Declarations
are not bank-derived positions, cash flows, valuations, income or repayments.
"""
from __future__ import annotations

import json
import os
import re

_GROUP_ID=re.compile(r"^[a-z][a-z0-9_]{2,39}$")
_LABEL=re.compile(r"^[^\x00-\x1f\x7f]{2,96}$")
_CATEGORIES=frozenset(("property","business","education","other"))
_ENV="P6B_PRIVATE_RELATIONSHIPS_JSON"


class PrivateInvestmentRegistryBlocked(ValueError):
    """The private, owner-only investment register needs review."""


def _strict_object(pairs):
    record={}
    for key,value in pairs:
        if key in record:
            raise ValueError()
        record[key]=value
    return record


def private_investment_relationships(*, property_verified:bool)->dict:
    raw=os.getenv(_ENV)
    if raw is None or raw=="":
        return {
            "contract":"personal_cfo_p6_owner_investment_registry_v1",
            "groups":[],
            "source":"PRIVATE_OWNER_DECLARATION",
            "property_register_group_id":None,
            "current_market_values_verified":False,
            "all_investment_contributions_reconciled":False,
        }
    try:
        if type(raw) is not str or len(raw)>4096:
            raise ValueError()
        obj=json.loads(raw,object_pairs_hook=_strict_object)
        if type(obj) is not dict or set(obj)!={"groups","property_register_group_id"}:
            raise ValueError()
        groups=obj["groups"]
        source_group=obj["property_register_group_id"]
        if (type(groups) is not list or not 1<=len(groups)<=10
            or type(source_group) is not str
            or not _GROUP_ID.fullmatch(source_group)):
            raise ValueError()
        seen=set()
        response=[]
        source_found=False
        for group in groups:
            if type(group) is not dict or set(group)!={"id","title","ventures"}:
                raise ValueError()
            group_id=group["id"]
            title=group["title"]
            ventures=group["ventures"]
            if (type(group_id) is not str or not _GROUP_ID.fullmatch(group_id)
                or group_id in seen
                or type(title) is not str or not _LABEL.fullmatch(title)
                or type(ventures) is not list or not 1<=len(ventures)<=4):
                raise ValueError()
            seen.add(group_id)
            used=set()
            listed=[]
            for venture in ventures:
                if type(venture) is not dict or set(venture)!={"id","title","category"}:
                    raise ValueError()
                v_id=venture["id"];v_title=venture["title"];cat=venture["category"]
                if (type(v_id) is not str or not _GROUP_ID.fullmatch(v_id)
                    or v_id in used
                    or type(v_title) is not str or not _LABEL.fullmatch(v_title)
                    or type(cat) is not str or cat not in _CATEGORIES):
                    raise ValueError()
                used.add(v_id)
                source_linked=group_id==source_group and cat=="property"
                if source_linked:
                    if source_found:
                        raise ValueError()
                    source_found=True
                listed.append({
                    "id":v_id,"title":v_title,"category":cat,
                    "evidence_status":(
                        "PROPERTY_REGISTER_RECONCILED_HISTORICAL_COSTS_ONLY"
                        if source_linked and property_verified else
                        "OWNER_DECLARED_AWAITING_TRANSACTION_ALLOCATION"),
                    "property_register_linked":source_linked and property_verified,
                    "confirmed_invested_principal_minor":None,
                    "current_market_value_minor":None,
                    "realized_cash_return_minor":None,
                    "expected_return_minor":None,
                })
            response.append({"id":group_id,"title":title,"ventures":listed,
                             "owner_declared":True})
        if not source_found:
            raise ValueError()
        return {
            "contract":"personal_cfo_p6_owner_investment_registry_v1",
            "groups":response,
            "source":"PRIVATE_OWNER_DECLARATION",
            "property_register_group_id":source_group,
            "current_market_values_verified":False,
            "all_investment_contributions_reconciled":False,
        }
    except (ValueError,TypeError,RecursionError,MemoryError):
        raise PrivateInvestmentRegistryBlocked(
            "Owner investment relationship settings require private review") from None
