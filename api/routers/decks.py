"""牌組 CRUD 端點。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Deck
from ..schemas import DeckRead, DeckWrite

router = APIRouter(prefix="/api/decks", tags=["decks"])


def _card_dicts(data: DeckWrite) -> list[dict]:
    return [card.model_dump(exclude_none=True) for card in data.cards]


@router.post("", response_model=DeckRead, status_code=201)
def create_deck(data: DeckWrite, session: Session = Depends(get_session)):
    deck = Deck(name=data.name, cards=_card_dicts(data))
    session.add(deck)
    session.commit()
    session.refresh(deck)
    return deck


@router.get("", response_model=list[DeckRead])
def list_decks(session: Session = Depends(get_session)):
    return session.exec(select(Deck)).all()


@router.get("/{deck_id}", response_model=DeckRead)
def get_deck(deck_id: int, session: Session = Depends(get_session)):
    deck = session.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="deck not found")
    return deck


@router.put("/{deck_id}", response_model=DeckRead)
def update_deck(deck_id: int, data: DeckWrite,
                session: Session = Depends(get_session)):
    deck = session.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="deck not found")
    deck.name = data.name
    deck.cards = _card_dicts(data)
    session.add(deck)
    session.commit()
    session.refresh(deck)
    return deck


@router.delete("/{deck_id}", status_code=204)
def delete_deck(deck_id: int, session: Session = Depends(get_session)):
    deck = session.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="deck not found")
    session.delete(deck)
    session.commit()
