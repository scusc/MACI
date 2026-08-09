#!/bin/bash
set -e

GW="http://20.120.28.42"
EMAIL="final_strict_$(date +%s)@rally.app"

echo "▶ 1. REGISTER"
HTTP_STATUS=$(curl -s -o /tmp/reg_out.txt -w "%{http_code}" -X POST $GW/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"TestPass123!\",\"first_name\":\"Kai\",\"last_name\":\"Nakamura\"}")
if [ "$HTTP_STATUS" -ne 200 ] && [ "$HTTP_STATUS" -ne 201 ]; then echo "❌ Register Failed ($HTTP_STATUS): $(cat /tmp/reg_out.txt)"; exit 1; fi
echo "  ✅ Registered: $EMAIL"

echo "▶ 2. LOGIN + GET TOKEN"
HTTP_STATUS=$(curl -s -o /tmp/login_out.txt -w "%{http_code}" -X POST $GW/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"TestPass123!\"}")
if [ "$HTTP_STATUS" -ne 200 ]; then echo "❌ Login Failed ($HTTP_STATUS): $(cat /tmp/login_out.txt)"; exit 1; fi
TOKEN=$(cat /tmp/login_out.txt | jq -r .token.access_token)
echo "  ✅ JWT Acquired"

echo "▶ 3. GET /me"
HTTP_STATUS=$(curl -s -o /tmp/me_out.txt -w "%{http_code}" -X GET $GW/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN")
if [ "$HTTP_STATUS" -ne 200 ]; then echo "❌ /me Failed ($HTTP_STATUS): $(cat /tmp/me_out.txt)"; exit 1; fi
echo "  ✅ Profile fetched"

echo "▶ 4. CREATE TRIP"
HTTP_STATUS=$(curl -s -o /tmp/trip_out.txt -w "%{http_code}" -X POST $GW/api/v1/trips \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Tokyo Strict Trip","description":"Verified trip","destination":"Tokyo","start_date":"2026-10-15","end_date":"2026-10-22","capacity":5,"is_private":false,"budget_tier":"mid","vibe_tags":["cyberpunk","tech"]}')
if [ "$HTTP_STATUS" -ne 200 ] && [ "$HTTP_STATUS" -ne 201 ]; then echo "❌ Trip Create Failed ($HTTP_STATUS): $(cat /tmp/trip_out.txt)"; exit 1; fi
TRIP_ID=$(cat /tmp/trip_out.txt | jq -r .id)
echo "  ✅ Trip Created: $TRIP_ID"

echo "▶ 5. POST /profile/quiz"
HTTP_STATUS=$(curl -s -o /tmp/quiz_out.txt -w "%{http_code}" -X POST $GW/api/v1/profile/quiz \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"social_battery":8,"budget_tolerance":5,"pacing":7,"spontaneity":9,"conflict_style":6,"travel_ethos":"Explore everything","dealbreakers":"No early mornings"}')
if [ "$HTTP_STATUS" -ne 200 ]; then echo "❌ Quiz Failed ($HTTP_STATUS): $(cat /tmp/quiz_out.txt)"; exit 1; fi
echo "  ✅ Psychometric Profile Updated"

echo "▶ 6. TRAVEL AI ITINERARY"
HTTP_STATUS=$(curl -s -o /tmp/ai_out.txt -w "%{http_code}" -X POST $GW/api/v1/travel/ai-itinerary \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"destination": "Tokyo", "days": 1, "budget": "Luxury", "travel_vibe": "Cyberpunk"}')
if [ "$HTTP_STATUS" -ne 200 ]; then echo "❌ AI Itinerary Failed ($HTTP_STATUS): $(cat /tmp/ai_out.txt)"; exit 1; fi
echo "  ✅ AI Response Generated"

echo "▶ 7. PAYMENT SERVICE CREATE"
HTTP_STATUS=$(curl -s -o /tmp/pay_out.txt -w "%{http_code}" -X POST $GW/api/v1/payments/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"pool_id\":\"$TRIP_ID\",\"member_id\":\"64127c3f-626c-40b2-8039-67ebbfb66781\",\"amount\":150000,\"currency\":\"USD\",\"gateway\":\"stripe\",\"payment_type\":\"slice_commit\"}")
if [ "$HTTP_STATUS" -ne 200 ] && [ "$HTTP_STATUS" -ne 201 ]; then echo "❌ Payment Create Failed ($HTTP_STATUS): $(cat /tmp/pay_out.txt)"; exit 1; fi
echo "  ✅ Payment Created"

echo ""
echo "✅ STRICT E2E COMPLETED WITH 100% SUCCESS"
