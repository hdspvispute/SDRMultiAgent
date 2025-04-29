from google.adk.tools.function_tool import FunctionTool

def create_lead(name: str, product: str, location: str, quantity: int) -> dict:
    return {
        "status": "success",
        "message": f"Lead created for {name}, product={product}, location={location}, quantity={quantity}"
    }

create_lead_tool = FunctionTool(func=create_lead)
