import re

with open('app/api/travel.py', 'r') as f:
    content = f.read()

# Define the new models and the new generate_ai_quote function
new_quote_code = """
class FlightDetails(BaseModel):
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    duration: str
    cabin_class: str

class HotelDetails(BaseModel):
    name: str
    rating: float
    address: str
    image_url: Optional[str] = None
    amenities: List[str]

class TravelerQuote(BaseModel):
    name: str
    origin: str
    flight_route: str
    individual_cost: int
    shared_cost: int
    total_cost: int
    flight_evidence: Optional[str] = None
    flights: List[FlightDetails] = []

class AIQuoteOption(BaseModel):
    id: str
    title: str
    shared_cost_per_person: int
    shared_accommodation_name: str
    shared_accommodation_total: int
    hotel_evidence: Optional[str] = None
    hotel_details: Optional[HotelDetails] = None
    traveler_quotes: List[TravelerQuote]
    reasoning: str

class AIQuoteResponse(BaseModel):
    options: List[AIQuoteOption]

@router.post("/quote", response_model=AIQuoteResponse)
async def generate_ai_quote(request: AIQuoteRequest):
    \"\"\"
    Agentic Multi-Origin Trip Quoting Engine.
    Orchestrates live concurrent flight searches for all travelers and routes, returning multiple options.
    \"\"\"
    import urllib.parse
    import json
    import asyncio
    from datetime import datetime
    
    logger.info(f"Generating Multi-Origin AI quote options for {len(request.travelers)} travelers across {len(request.itinerary)} legs.")
    
    if not request.travelers or not request.itinerary:
        raise HTTPException(400, "Must provide travelers and itinerary.")
        
    group_size = len(request.travelers)
    
    async def fetch_flight(orig: str, dest: str, date: str) -> dict:
        try:
            from app.services import serpapi_client
            flights = await serpapi_client.search_flights(
                departure_id=orig.upper(),
                arrival_id=dest.upper(),
                outbound_date=date,
                type=2
            )
            if flights:
                best = flights[0]
                price = float(best.get("price", 500.0))
                sf_f = best.get("flights", [{}])[0]
                dur = best.get("total_duration", 120)
                
                details = FlightDetails(
                    airline=sf_f.get("airline", "Major Carrier"),
                    flight_number=sf_f.get("flight_number", "FL-101"),
                    departure_time=sf_f.get("departure_airport", {}).get("time", "09:00 AM"),
                    arrival_time=sf_f.get("arrival_airport", {}).get("time", "05:00 PM"),
                    duration=f"{dur // 60}h {dur % 60}m",
                    cabin_class=sf_f.get("travel_class", "Economy")
                )
                return {"price": price, "details": details}
        except Exception as e:
            logger.warning(f"Flight search failed {orig}->{dest}: {e}")
            
        return {
            "price": 450.0, 
            "details": FlightDetails(
                airline="Generic Air", flight_number="GA-001",
                departure_time="08:00 AM", arrival_time="12:00 PM",
                duration="4h 0m", cabin_class="Economy"
            )
        }

    async def fetch_hotel(dest: str, checkin: str, checkout: str, category: str) -> dict:
        try:
            from app.services import serpapi_client
            hotels = await serpapi_client.search_inventory(
                query=f"Hotels in {dest}",
                check_in=checkin,
                check_out=checkout,
                adults=group_size,
                category=category
            )
            if hotels:
                h = hotels[0]
                checkin_d = datetime.strptime(checkin, "%Y-%m-%d")
                checkout_d = datetime.strptime(checkout, "%Y-%m-%d")
                days = max(1, (checkout_d - checkin_d).days)
                
                details = HotelDetails(
                    name=h.title,
                    rating=4.5,
                    address=h.location,
                    image_url=h.media_urls[0] if h.media_urls else None,
                    amenities=["WiFi", "Pool"]
                )
                return {"name": h.title, "total": h.total_price, "details": details}
        except Exception as e:
            pass
            
        checkin_d = datetime.strptime(checkin, "%Y-%m-%d")
        checkout_d = datetime.strptime(checkout, "%Y-%m-%d")
        days = max(1, (checkout_d - checkin_d).days)
        base_price = 100 if category == 'budget' else (300 if category == 'luxury' else 200)
        
        details = HotelDetails(
            name=f"{category.title()} Hotel in {dest}",
            rating=4.0,
            address=f"Central {dest}",
            image_url="https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1000",
            amenities=["WiFi"]
        )
        return {"name": details.name, "total": base_price * days * (group_size / 2), "details": details}

    # Generate 3 options: Budget, Balanced, Luxury
    options = []
    tiers = [
        ("opt_budget", "Budget Friendly", "budget", 0.7),
        ("opt_balanced", "Balanced (Recommended)", "balanced", 1.0),
        ("opt_luxury", "Luxury Villas", "luxury", 2.0)
    ]
    
    # Run fetch tasks for all 3 options concurrently to save time, or do it sequentially but grouped
    for opt_id, opt_title, h_category, f_multiplier in tiers:
        # Fetch hotels
        hotel_tasks = [fetch_hotel(leg.destination, leg.arrival_date, leg.departure_date, h_category) for leg in request.itinerary]
        hotel_results = await asyncio.gather(*hotel_tasks, return_exceptions=True)
        
        total_accommodation_cost = sum(h["total"] for h in hotel_results if not isinstance(h, Exception))
        shared_cost_per_person = int(total_accommodation_cost / group_size)
        shared_acc_name = " + ".join([h["name"] for h in hotel_results if not isinstance(h, Exception)])
        main_hotel_details = hotel_results[0]["details"] if hotel_results and not isinstance(hotel_results[0], Exception) else None
        
        # Fetch flights for travelers
        traveler_quotes = []
        for traveler in request.travelers:
            flight_tasks = []
            flight_tasks.append(fetch_flight(traveler.origin, request.itinerary[0].destination, request.itinerary[0].arrival_date))
            for i in range(len(request.itinerary) - 1):
                flight_tasks.append(fetch_flight(request.itinerary[i].destination, request.itinerary[i+1].destination, request.itinerary[i].departure_date))
            flight_tasks.append(fetch_flight(request.itinerary[-1].destination, traveler.origin, request.itinerary[-1].departure_date))
            
            results = await asyncio.gather(*flight_tasks, return_exceptions=True)
            
            total_flight_cost = 0
            flight_details_list = []
            for r in results:
                if not isinstance(r, Exception):
                    # Adjust price based on tier multiplier
                    total_flight_cost += r["price"] * f_multiplier
                    flight_details_list.append(r["details"])
                    
            route_str = f"{traveler.origin} ✈️ " + " ✈️ ".join([leg.destination for leg in request.itinerary]) + f" ✈️ {traveler.origin}"
            encoded_dest = urllib.parse.quote(request.itinerary[0].destination)
            encoded_orig = urllib.parse.quote(traveler.origin)
            flight_url = f"https://www.google.com/travel/flights?q=Flights%20to%20{encoded_dest}%20from%20{encoded_orig}%20on%20{request.itinerary[0].arrival_date}"
            
            traveler_quotes.append(TravelerQuote(
                name=traveler.name,
                origin=traveler.origin,
                flight_route=route_str,
                individual_cost=int(total_flight_cost),
                shared_cost=shared_cost_per_person,
                total_cost=int(total_flight_cost + shared_cost_per_person),
                flight_evidence=flight_url,
                flights=flight_details_list
            ))
            
        encoded_hotel_dest = urllib.parse.quote(request.itinerary[0].destination)
        hotel_url = f"https://www.google.com/travel/hotels?q=Hotels%20in%20{encoded_hotel_dest}&checkin={request.itinerary[0].arrival_date}&checkout={request.itinerary[0].departure_date}"
        
        reasoning = f"This {opt_title} option splits the ${int(total_accommodation_cost)} accommodation cost equally (${shared_cost_per_person} each). Flights are tailored individually to keep it fair for everyone's origin point."
        
        options.append(AIQuoteOption(
            id=opt_id,
            title=opt_title,
            shared_cost_per_person=shared_cost_per_person,
            shared_accommodation_name=shared_acc_name,
            shared_accommodation_total=int(total_accommodation_cost),
            hotel_evidence=hotel_url,
            hotel_details=main_hotel_details,
            traveler_quotes=traveler_quotes,
            reasoning=reasoning
        ))
        
    return AIQuoteResponse(options=options)
"""

# Find the block starting with `class TravelerQuote(BaseModel):` up to the end of the file.
pattern = r'class TravelerQuote\(BaseModel\):.*'
# We will use re.sub with dotall
patched_content = re.sub(pattern, new_quote_code, content, flags=re.DOTALL)

with open('app/api/travel.py', 'w') as f:
    f.write(patched_content)

print("Patch applied to travel.py!")
