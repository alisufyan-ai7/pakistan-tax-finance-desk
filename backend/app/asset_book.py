"""Synthetic-only encrypted, immutable declared investment/property asset snapshots.

All personally meaningful values, dates, labels and quantities live inside the
AES-GCM encrypted payload. The DB indexes only random envelope IDs/timestamps.
Owner-declared values are not independently verified or a tax basis; no broker
trades, gains, market prices or financial advice are computed automatically.
"""
from __future__ import annotations
from datetime import date
from typing import Literal
from decimal import Decimal, InvalidOperation
import json
import uuid
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import AssetSnapshot

KINDS={'equity','mutual_fund','crypto','gold','real_estate','vehicle','fixed_deposit','other_asset','other_liability'}
MAX_MINOR=10**15

class AssetInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    synthetic_fixture: Literal[True]
    position_id: str | None = Field(default=None,min_length=36,max_length=36)
    kind: str
    label: str=Field(min_length=3,max_length=160)
    as_of: date
    acquired_on: date | None=None
    quantity: str | None=None
    cost_basis_minor: StrictInt | None=Field(default=None,ge=0,le=MAX_MINOR)
    declared_value_minor: StrictInt | None=Field(default=None,ge=0,le=MAX_MINOR)
    legal_owner: str='individual'
    currency: str='PKR'
    evidence_basis: str=Field(min_length=12,max_length=500)

    @model_validator(mode='after')
    def allowed(self):
        if self.synthetic_fixture is not True:
            raise ValueError('Only explicitly marked synthetic fixtures accepted')
        if self.kind not in KINDS or self.legal_owner!='individual' or self.currency!='PKR':
            raise ValueError('Only declared individual PKR fixture assets supported')
        if self.position_id:
            try: uuid.UUID(self.position_id)
            except (ValueError,AttributeError): raise ValueError('position_id must be a UUID') from None
        if self.acquired_on and self.acquired_on>self.as_of:
            raise ValueError('Acquisition date cannot be after declared valuation date')
        if not date(1900,1,1)<=self.as_of<=date(2100,12,31):
            raise ValueError('Unsupported date')
        if self.quantity is not None:
            try:
                q=Decimal(self.quantity)
            except (InvalidOperation,ValueError,TypeError) as exc:
                raise ValueError('Quantity must be a positive decimal string') from exc
            if not q.is_finite() or q<=0 or q.as_tuple().exponent < -6 or q>Decimal('1e12'):
                raise ValueError('Quantity must have <=6 decimals and be positive')
        if not self.label.strip() or not self.evidence_basis.strip():
            raise ValueError('Label and evidence basis cannot be blank')
        if self.cost_basis_minor is None and self.declared_value_minor is None:
            raise ValueError('At least one value must be explicitly provided')
        return self


def _unwrap(snapshot: AssetSnapshot) -> dict:
    # EncryptedText transparently decrypts; strict format prevents silent legacy values.
    return json.loads(snapshot.payload_json)


def _all(db: Session):
    return [(row,_unwrap(row)) for row in db.scalars(select(AssetSnapshot)).all()]


def record_asset(db: Session, payload: AssetInput):
    existing=_all(db)
    identifier=payload.position_id or str(uuid.uuid4())
    if payload.position_id and not any(p['position_id']==identifier for _,p in existing):
        raise HTTPException(404,'Asset position to update not found')
    if payload.position_id:
        prior=[p for _,p in existing if p['position_id']==identifier]
        if any(p['kind']!=payload.kind or p['currency']!=payload.currency or p['legal_owner']!=payload.legal_owner for p in prior):
            raise HTTPException(409,'Asset kind, owner and currency cannot change between snapshots')
    obj=payload.model_dump(mode='json')
    obj['position_id']=identifier
    date_key=obj['as_of']
    for row,p in existing:
        if p['position_id']==identifier and p['as_of']==date_key:
            if p==obj:
                return {'position_id':identifier,'snapshot_id':row.id,'already_recorded':True,'synthetic_only':True,'valuation_verified':False},True
            raise HTTPException(409,'Conflicting snapshot already exists for that position/date; audited correction needed')
    record=AssetSnapshot(id=str(uuid.uuid4()),payload_json=json.dumps(obj,sort_keys=True,separators=(',',':')))
    db.add(record)
    db.commit()
    return {'position_id':identifier,'snapshot_id':record.id,'already_recorded':False,'synthetic_only':True,'valuation_verified':False},False


def asset_position(db: Session, as_of: date) -> dict:
    if not date(1900,1,1)<=as_of<=date(2100,12,31):
        raise HTTPException(422,'Unsupported valuation date')
    data:dict[str,list[dict]]={}
    for row,p in _all(db):
        if date.fromisoformat(p['as_of'])<=as_of:
            data.setdefault(p['position_id'],[]).append(dict(p,snapshot_id=row.id))
    positions=[]
    for values in data.values():
        latest=max(values,key=lambda p:(p['as_of'],p['snapshot_id']))
        latest['source']='OWNER_DECLARED_SYNTHETIC'
        latest['valuation_verified']=False
        latest['evidence_review_required']=True
        positions.append(latest)
    positions.sort(key=lambda p:(p['kind'],p['position_id']))
    # Known/unknown totals are separate. A missing declared value cannot count as zero.
    included=[p for p in positions if p['declared_value_minor'] is not None]
    excluded=[p for p in positions if p['declared_value_minor'] is None]
    assets=sum(p['declared_value_minor'] for p in included if p['kind']!='other_liability')
    liabilities=sum(p['declared_value_minor'] for p in included if p['kind']=='other_liability')
    complete=bool(positions) and not excluded
    return {'as_of':as_of.isoformat(),'synthetic_only':True,'positions':positions,
        'registered_snapshot_count':len(positions),'unvalued_position_count':len(excluded),
        'declared_asset_components_minor':assets if complete else None,
        'declared_liability_components_minor':liabilities if complete else None,
        'declared_component_difference_minor':(assets-liabilities) if complete else None,
        'net_worth_minor':None,'realized_gain_minor':None,'capital_gains_tax_minor':None,
        'tax_due_minor':None,'fbr_wealth_reconciled':False,'market_prices_verified':False,
        'warning':'This is owner-declared position snapshots, not verified holdings, tax basis, gains or full net worth.'}