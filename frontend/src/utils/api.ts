interface Listing {
  id: number
  platform_id: string
  platform_name: string
  source_url: string
  title: string | null
  description: string | null
  listing_type: string | null
  property_type: string | null
  price_amount: number | null
  price_currency: string | null
  price_period: string | null
  location_text: string | null
  location: string | null
  bedrooms: number | null
  bathrooms: number | null
  size_value: number | null
  size_unit: string | null
  agent_name: string | null
  agency_name: string | null
  agency_url: string | null
  phone_numbers: string[]
  whatsapp_numbers: string[]
  emails: string[]
  contact_reveal_method: string | null
  date_posted: string | null
  first_seen_at: string
  last_seen_at: string
  duplicate_of_id: number | null
}

interface Platform {
  id: string
  name: string
}

interface Filters {
  listing_type: string
  location: string
  min_price: string
  max_price: string
  min_bedrooms: string
  platform: string
  has_phone: string
  sort: string
}

const API = '/api'

function fetchListings(filters: Filters, offset: number, limit: number): Promise<{ items: Listing[]; total_count: number; has_more: boolean }> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (filters.listing_type) params.set('listing_type', filters.listing_type)
  if (filters.location) params.set('location', filters.location)
  if (filters.min_price) params.set('min_price', filters.min_price)
  if (filters.max_price) params.set('max_price', filters.max_price)
  if (filters.min_bedrooms) params.set('min_bedrooms', filters.min_bedrooms)
  if (filters.platform) params.set('platform', filters.platform)
  if (filters.has_phone) params.set('has_phone', filters.has_phone)
  if (filters.sort) params.set('sort', filters.sort)
  
  return fetch(`${API}/listings?${params}`).then(r => r.json())
}

function fetchPlatforms(): Promise<Platform[]> {
  return fetch('/api/platforms').then(r => r.json()).catch(() => [])
}

function searchByPhone(phone: string, limit: number): Promise<{ items: Listing[]; total_count: number }> {
  return fetch(`${API}/search?phone=${encodeURIComponent(phone)}&limit=${limit}`).then(r => r.json())
}

function sendChatMessage(messages: {role: string; content: string}[]): Promise<{ reply: string }> {
  return fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  }).then(r => r.json())
}

export { fetchListings, fetchPlatforms, searchByPhone, sendChatMessage }