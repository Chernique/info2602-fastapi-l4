from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.database import SessionDep
from app.models import *
from app.auth import AuthDep

todo_router = APIRouter(tags=["Todo Management"])

@todo_router.get('/todos', response_model=list[TodoResponse])
def get_todos(db: SessionDep, user: AuthDep):
    todos = user.todos
    result = []
    for todo in todos:
        todo_response = TodoResponse(
            id=todo.id,
            text=todo.text,
            done=todo.done,
            categories=[CategoryItem(id=cat.id, text=cat.text) for cat in todo.categories]
        )
        result.append(todo_response)
    return result

@todo_router.get('/todo/{id}', response_model=TodoResponse)
def get_todo_by_id(id: int, db: SessionDep, user: AuthDep):
    todo = db.exec(select(Todo).where(Todo.id == id, Todo.user_id == user.id)).one_or_none()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TodoResponse(
        id=todo.id,
        text=todo.text,
        done=todo.done,
        categories=[CategoryItem(id=cat.id, text=cat.text) for cat in todo.categories]
    )

@todo_router.post('/todos', response_model=TodoResponse)
def create_todo(db: SessionDep, user: AuthDep, todo_data: TodoCreate):
    todo = Todo(text=todo_data.text, user_id=user.id)
    try:
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return TodoResponse(
            id=todo.id,
            text=todo.text,
            done=todo.done,
            categories=[]
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while creating an item",
        )

@todo_router.put('/todo/{id}', response_model=TodoResponse)
def update_todo(id: int, db: SessionDep, user: AuthDep, todo_data: TodoUpdate):
    todo = db.exec(select(Todo).where(Todo.id == id, Todo.user_id == user.id)).one_or_none()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    if todo_data.text is not None:
        todo.text = todo_data.text
    if todo_data.done is not None:
        todo.done = todo_data.done
    try:
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return TodoResponse(
            id=todo.id,
            text=todo.text,
            done=todo.done,
            categories=[CategoryItem(id=cat.id, text=cat.text) for cat in todo.categories]
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while updating an item",
        )

@todo_router.delete('/todo/{id}', status_code=status.HTTP_200_OK)
def delete_todo(id: int, db: SessionDep, user: AuthDep):
    todo = db.exec(select(Todo).where(Todo.id == id, Todo.user_id == user.id)).one_or_none()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    try:
        db.delete(todo)
        db.commit()
        return {"message": "Todo deleted successfully"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while deleting an item",
        )

@todo_router.post('/category', response_model=CategoryItem, status_code=status.HTTP_201_CREATED)
def create_category(db: SessionDep, user: AuthDep, category_data: TodoCreate):
    try:
        category = Category(
            text=category_data.text,
            user_id=user.id
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return CategoryItem(id=category.id, text=category.text)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while creating the category",
        )

@todo_router.post('/todo/{todo_id}/category/{cat_id}', status_code=status.HTTP_200_OK)
def add_category_to_todo(todo_id: int, cat_id: int, db: SessionDep, user: AuthDep):
    todo = db.exec(select(Todo).where(Todo.id == todo_id, Todo.user_id == user.id)).one_or_none()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Todo not found or unauthorized",
        )
    
    category = db.exec(select(Category).where(Category.id == cat_id, Category.user_id == user.id)).one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or unauthorized",
        )
    
    if category in todo.categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category already assigned to this todo",
        )
    
    todo.categories.append(category)
    try:
        db.add(todo)
        db.commit()
        return {"message": f"Category '{category.text}' added to todo successfully"}
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while adding category to todo",
        )

@todo_router.delete('/todo/{todo_id}/category/{cat_id}', status_code=status.HTTP_200_OK)
def remove_category_from_todo(todo_id: int, cat_id: int, db: SessionDep, user: AuthDep):
    todo = db.exec(select(Todo).where(Todo.id == todo_id, Todo.user_id == user.id)).one_or_none()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Todo not found or unauthorized",
        )
    
    category = db.exec(select(Category).where(Category.id == cat_id, Category.user_id == user.id)).one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or unauthorized",
        )
    
    if category not in todo.categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category is not assigned to this todo",
        )
    
    todo.categories.remove(category)
    try:
        db.add(todo)
        db.commit()
        return {"message": f"Category '{category.text}' removed from todo successfully"}
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while removing category from todo",
        )

@todo_router.get('/category/{cat_id}/todos', response_model=list[TodoResponse])
def get_todos_for_category(cat_id: int, db: SessionDep, user: AuthDep):
    category = db.exec(select(Category).where(Category.id == cat_id, Category.user_id == user.id)).one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or unauthorized",
        )
    
    result = []
    for todo in category.todos:
        if todo.user_id == user.id:
            todo_response = TodoResponse(
                id=todo.id,
                text=todo.text,
                done=todo.done,
                categories=[CategoryItem(id=cat.id, text=cat.text) for cat in todo.categories]
            )
            result.append(todo_response)
    
    return result