from fastapi.responses import JSONResponse

def success_response(data):
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "data": data
        }
    )

def error_response(message):
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": message
        }
    )