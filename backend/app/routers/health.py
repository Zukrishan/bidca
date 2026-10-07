from fastapi import APIRouter


router = APIRouter()


# Health check
@router.get("/")
async def root():
    return {"message": "BidCa.ca API - Full Auction Platform", "status": "running"}

@router.get("/health")
async def health():
    return {"status": "healthy"}
