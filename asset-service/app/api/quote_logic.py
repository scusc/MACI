class Traveler(BaseModel):
    name: str
    origin: str

class TripLeg(BaseModel):
    destination: str
    arrival_date: str
    departure_date: str

class AIQuoteRequest(BaseModel):
    travelers: List[Traveler]
    itinerary: List[TripLeg]
    budget_tier: str = "balanced"

class TravelerQuote(BaseModel):
    name: str
    origin: str
    flight_route: str
    individual_cost: int
    shared_cost: int
    total_cost: int
    flight_evidence: Optional[str] = None

class AIQuoteResponse(BaseModel):
    shared_cost_per_person: int
    shared_accommodation_name: str
    shared_accommodation_total: int
    hotel_evidence: Optional[str] = None
    traveler_quotes: List[TravelerQuote]
    reasoning: str

@router.post("/quote", response_model=AIQuoteResponse)
async def generate_ai_quote(request: AIQuoteRequest):
    """
    Agentic Multi-Origin Trip Quoting Engine.
    Orchestrates live concurrent flight searches for all travelers and routes.
    """
    import urllib.parse
    import json
    import asyncio
    from datetime import datetime
    
    logger.info(f"Generating Multi-Origin AI quote for {len(request.travelers)} travelers across {len(request.itinerary)} legs.")
    
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
                airline = best.get("flights", [{}])[0].get("airline", "Major Carrier")
                return {"price": price, "airline": airline}
        except Exception as e:
            logger.warning(f"Flight search failed {orig}->{dest}: {e}")
        return {"price": 450.0, "airline": "Generic Airline"}

    async def fetch_hotel(dest: str, checkin: str, checkout: str) -> dict:
        try:
            from app.services import serpapi_client
            hotels = await serpapi_client.search_inventory(
                query=f"Villas in {dest}",
                check_in=checkin,
                check_out=checkout,
                adults=group_size,
                category=request.budget_tier
            )
            if hotels:
                sorted_hotels = sorted(hotels, key=lambda x: x.price_per_night_usd)
                if request.budget_tier == "budget": h = sorted_hotels[0]
                elif request.budget_tier == "luxury": h = sorted_hotels[-1]
                else: h = sorted_hotels[len(sorted_hotels)//2]
                
                checkin_d = datetime.strptime(checkin, "%Y-%m-%d")
                checkout_d = datetime.strptime(checkout, "%Y-%m-%d")
                days = max(1, (checkout_d - checkin_d).days)
                return {"name": h.name, "total": h.price_per_night_usd * days}
        except Exception as e:
            pass
            
        checkin_d = datetime.strptime(checkin, "%Y-%m-%d")
        checkout_d = datetime.strptime(checkout, "%Y-%m-%d")
        days = max(1, (checkout_d - checkin_d).days)
        return {"name": f"Group Accommodation in {dest}", "total": 200.0 * days * (group_size / 2)}

    # 1. Fetch all hotels concurrently
    hotel_tasks = [fetch_hotel(leg.destination, leg.arrival_date, leg.departure_date) for leg in request.itinerary]
    hotel_results = await asyncio.gather(*hotel_tasks)
    
    total_accommodation_cost = sum(h["total"] for h in hotel_results)
    shared_cost_per_person = int(total_accommodation_cost / group_size)
    shared_acc_name = " + ".join([h["name"] for h in hotel_results])
    
    # 2. Fetch all flights concurrently for all travelers
    traveler_quotes = []
    
    # We create a task matrix: for each traveler, we need inbound, intra-leg (if any), and outbound flights.
    for traveler in request.travelers:
        flight_tasks = []
        # Inbound
        flight_tasks.append(fetch_flight(traveler.origin, request.itinerary[0].destination, request.itinerary[0].arrival_date))
        # Intra-leg
        for i in range(len(request.itinerary) - 1):
            flight_tasks.append(fetch_flight(request.itinerary[i].destination, request.itinerary[i+1].destination, request.itinerary[i].departure_date))
        # Outbound
        flight_tasks.append(fetch_flight(request.itinerary[-1].destination, traveler.origin, request.itinerary[-1].departure_date))
        
        results = await asyncio.gather(*flight_tasks)
        
        total_flight_cost = sum(r["price"] for r in results)
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
            flight_evidence=flight_url
        ))

    encoded_hotel_dest = urllib.parse.quote(request.itinerary[0].destination)
    hotel_url = f"https://www.google.com/travel/hotels?q=Hotels%20in%20{encoded_hotel_dest}&checkin={request.itinerary[0].arrival_date}&checkout={request.itinerary[0].departure_date}"
    
    # 3. Ask AI to evaluate the logistics
    prompt_context = f"""
    You are an elite travel strategist for Rally.
    Group Size: {group_size} people.
    Itinerary: {[leg.destination for leg in request.itinerary]}
    Total Shared Accommodation: ${int(total_accommodation_cost)} (Split {group_size} ways = ${shared_cost_per_person}/person).
    Travelers:
    """
    for tq in traveler_quotes:
        prompt_context += f"- {tq.name} ({tq.origin}): Flight Cost ${tq.individual_cost} Total: ${tq.total_cost}\n"
        
    prompt_context += """
    TASK: Write a highly thoughtful, 3-sentence `reasoning` evaluating the logistics. Mention why treating accommodation as a shared cost but flights individually is the fairest approach for this specific group. Make the user feel they are getting expert advice.
    
    Respond ONLY in valid JSON format matching exactly:
    {
      "reasoning": "Your 3-sentence expert advice here."
    }
    """
    
    try:
        from app.services.ai_delegate import get_azure_openai_client
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = get_azure_openai_client()
        sys_msg = SystemMessage(content="You are a data-driven travel strategist. Output ONLY valid JSON.")
        response = await llm.ainvoke([sys_msg, HumanMessage(content=prompt_context)])
        
        content = response.content
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
            
        data = json.loads(content.strip())
        reasoning = data.get("reasoning", "Expert reasoning unavailable.")
    except Exception as e:
        logger.warning(f"AI Quote Reasoning failed: {e}")
        reasoning = f"By splitting the ${int(total_accommodation_cost)} accommodation equally, everyone pays a fair base rate. Individual flights are kept separate so nobody subsidizes someone else's expensive route. This multi-origin strategy ensures perfectly equitable pricing across the board."

    return AIQuoteResponse(
        shared_cost_per_person=shared_cost_per_person,
        shared_accommodation_name=shared_acc_name,
        shared_accommodation_total=int(total_accommodation_cost),
        hotel_evidence=hotel_url,
        traveler_quotes=traveler_quotes,
        reasoning=reasoning
    )
