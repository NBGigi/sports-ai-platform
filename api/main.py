from fastapi import (
    FastAPI,
    HTTPException,
)

from database.connection import (
    get_connection,
)

from database.queries import (
    get_upcoming_fixture_predictions,
)

from modeling.live_prediction import (
    predict_live_fixture,
)


MODEL_VERSION = "v1"


app = FastAPI(
    title="Sports AI Platform",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "sports-ai-api",
    }


@app.get(
    "/predictions/upcoming"
)
def upcoming_predictions(
    limit: int = 10,
):
    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail=(
                "limit must be "
                "between 1 and 50"
            ),
        )

    connection = get_connection()

    try:
        predictions = (
            get_upcoming_fixture_predictions(
                connection,
                model_version=MODEL_VERSION,
                limit=limit,
            )
        )

    finally:
        connection.close()

    return {
        "model_version":
            MODEL_VERSION,

        "count":
            len(predictions),

        "predictions":
            predictions,
    }


@app.get(
    "/predictions/live/{fixture_id}"
)
def live_prediction(
    fixture_id: int,
):
    try:
        prediction = (
            predict_live_fixture(
                fixture_id=fixture_id,
                model_version=MODEL_VERSION,
            )
        )

    except ValueError as error:
        message = str(error)

        if (
            "not found"
            in message.lower()
        ):
            status_code = 404

        else:
            status_code = 400

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from error

    return prediction