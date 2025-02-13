from typing import Annotated

from fastapi import Path, APIRouter

router = APIRouter(prefix='/items')

@router.get('/')
def list_items():
    return [
        "Item1",
        "Item2",
    ]

@router.get('/latest/')
def get_latest_item():
    return {'Item': {'id': '0', 'name': 'latest'}}

@router.get('/{item_id}')
def get_item_by_id(item_id: Annotated[int, Path(ge=1, le=1_000_000)]):
    return {'item': item_id}

