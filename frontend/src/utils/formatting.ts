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

function formatPrice(amount: number | null, currency: string | null, period: string | null): string {
  if (amount === null) return '—'
  const fmt = new Intl.NumberFormat('en-KE', { style: 'currency', currency: currency || 'KES', maximumFractionDigits: 0 }).format(amount)
  return period ? `${fmt}/${period}` : fmt
}

function formatDate(date: string | null): string {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('en-KE', { year: 'numeric', month: 'short', day: 'numeric' })
}

function waLink(phone: string): string {
  let n = phone.replace(/[\s\-\+\(\)]/g, '')
  if (n.startsWith('0')) n = '254' + n.slice(1)
  if (!n.startsWith('254')) n = '254' + n
  return `https://wa.me/${n}`
}

function composeMessage(listing: Listing): string {
  const agent = listing.agent_name || listing.agency_name || 'Sir/Madam'
  const property = listing.title?.toUpperCase() ||
    (listing.bedrooms ? `${listing.bedrooms} BEDROOM ${(listing.property_type || 'PROPERTY').toUpperCase()}` : 'THIS PROPERTY')
  const location = listing.location_text || listing.location
  const price = formatPrice(listing.price_amount, listing.price_currency, listing.price_period)
  const parts = [`Hello ${agent} I would like to check the availability for ${property}`]
  if (location) parts.push(`, ${location}`)
  parts.push(`, ${price} Thank you!`)
  return parts.join('')
}

function waMsgLink(phone: string, message: string): string {
  return `${waLink(phone)}?text=${encodeURIComponent(message)}`
}

export { formatPrice, formatDate, waLink, composeMessage, waMsgLink }