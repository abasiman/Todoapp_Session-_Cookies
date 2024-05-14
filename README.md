# ToDo App REST API

This is a REST API designed to manage ToDo items and Completed items for the ToDo application.

## Endpoints

### TodoList

- `POST /TodoList/`: Create a new ToDo item.
- `GET /TodoList/`: Retrieve all ToDo items.
- `DELETE /TodoList/{todo_id}/`: Delete a ToDo item by its ID.
- `PUT /TodoList/{todo_id}/`: Update a ToDo item by its ID.
- `DELETE /TodoList/`: Clear all ToDo items.

### CompletedList

- `POST /CompletedList/`: Create a new Completed item.
- `GET /CompletedList/`: Retrieve all Completed items.
- `DELETE /CompletedList/`: Clear all Completed items.

## Data Models

### TodoBase

```json
{
  "newItem": "string"
}
```

### TodoModel
```json
{
  "id": "integer",
  "newItem": "string"
}
```

### CompletedBase
```json
{
  "completedItem": "string"
}
```

### CompletedModel
```json
{
  "id": "integer",
  "completedItem": "string"
}
```

## Dependencies
- Python 3.10.12
- FastAPI
- SQLAlchemy
- Pydantic


## Usage
1. Install dependencies: `pip install -r requirements.txt`
2. Run the FastAPI server: `uvicorn main:app --reload`
3. Access the API at `http://localhost:your-port/`


## CORS Configuration
- Allowed Methods: GET, POST, PUT, DELETE
- Allowed Headers: All headers allowed
- Credentials: Allowed# DbIntegratedApp-
