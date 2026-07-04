import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

const API = '/api'

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

interface PaginatedResult {
  items: Listing[]
  total_count: number
  has_more: boolean
  offset: number
  limit: number
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

const defaultFilters: Filters = {
  listing_type: '',
  location: '',
  min_price: '',
  max_price: '',
  min_bedrooms: '',
  platform: '',
  has_phone: '',
  sort: 'newest',
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

function Badge({ label, color }: { label: string; color: string }) {
  return <span className={`badge badge-${color}`}>{label}</span>
}

export default function App() {
  const [listings, setListings] = useState<Listing[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [platforms, setPlatforms] = useState<Platform[]>([])
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [contactListing, setContactListing] = useState<Listing | null>(null)
  const [searchPhone, setSearchPhone] = useState('')
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState<{role: string; content: string}[]>([
    {role: 'assistant', content: 'Hi! I\'m Agent Eve. I can help you find the perfect property in Kenya. Tell me what you\'re looking for!'},
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const limit = 25

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const fetchListings = useCallback(async (ofs: number) => {
    setLoading(true)
    const params = new URLSearchParams({ limit: String(limit), offset: String(ofs) })
    if (filters.listing_type) params.set('listing_type', filters.listing_type)
    if (filters.location) params.set('location', filters.location)
    if (filters.min_price) params.set('min_price', filters.min_price)
    if (filters.max_price) params.set('max_price', filters.max_price)
    if (filters.min_bedrooms) params.set('min_bedrooms', filters.min_bedrooms)
    if (filters.platform) params.set('platform', filters.platform)
    if (filters.has_phone) params.set('has_phone', filters.has_phone)
    if (filters.sort) params.set('sort', filters.sort)
    try {
      const res = await fetch(`${API}/listings?${params}`)
      const data: PaginatedResult = await res.json()
      setListings(data.items)
      setTotalCount(data.total_count)
      setOffset(ofs)
    } catch { /* ignore */ }
    setLoading(false)
  }, [filters])

  useEffect(() => {
    fetch('/api/platforms').then(r => r.json()).then(setPlatforms).catch(() => {})
    fetchListings(0)
  }, [fetchListings])

  const handleSearchPhone = async () => {
    if (!searchPhone.trim()) return
    setLoading(true)
    try {
      const res = await fetch(`${API}/search?phone=${encodeURIComponent(searchPhone.trim())}&limit=${limit}`)
      const data: PaginatedResult = await res.json()
      setListings(data.items)
      setTotalCount(data.total_count)
      setOffset(0)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const handleChatSend = async () => {
    const text = chatInput.trim()
    if (!text || chatLoading) return
    setChatInput('')
    const userMsg = { role: 'user', content: text }
    const updated = [...chatMessages, userMsg]
    setChatMessages(updated)
    setChatLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: updated }),
      })
      const data = await res.json()
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I\'m having trouble connecting right now.' }])
    }
    setChatLoading(false)
  }

  const totalPages = Math.ceil(totalCount / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="app">
      <header className="header">
        <h1>Kenya Property Listings</h1>
        <p className="subtitle">{totalCount} listings across {platforms.length} platforms</p>
      </header>

      <div className="filters">
        <div className="filter-grid">
          <div className="filter-group">
            <label>Type</label>
            <select value={filters.listing_type} onChange={e => setFilters(f => ({ ...f, listing_type: e.target.value }))}>
              <option value="">All</option>
              <option value="sale">For Sale</option>
              <option value="rent">For Rent</option>
            </select>
          </div>
          <div className="filter-group">
            <label>Location</label>
            <input
              type="text" placeholder="e.g. Parklands, Westlands"
              value={filters.location}
              onChange={e => setFilters(f => ({ ...f, location: e.target.value }))}
            />
          </div>
          <div className="filter-group">
            <label>Min Price (KES)</label>
            <input
              type="number" placeholder="0"
              value={filters.min_price}
              onChange={e => setFilters(f => ({ ...f, min_price: e.target.value }))}
            />
          </div>
          <div className="filter-group">
            <label>Max Price (KES)</label>
            <input
              type="number" placeholder="10000000"
              value={filters.max_price}
              onChange={e => setFilters(f => ({ ...f, max_price: e.target.value }))}
            />
          </div>
          <div className="filter-group">
            <label>Bedrooms</label>
            <select value={filters.min_bedrooms} onChange={e => setFilters(f => ({ ...f, min_bedrooms: e.target.value }))}>
              <option value="">Any</option>
              {[1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n}+</option>)}
            </select>
          </div>
          <div className="filter-group">
            <label>Platform</label>
            <select value={filters.platform} onChange={e => setFilters(f => ({ ...f, platform: e.target.value }))}>
              <option value="">All</option>
              {platforms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="filter-group">
            <label>Has Phone</label>
            <select value={filters.has_phone} onChange={e => setFilters(f => ({ ...f, has_phone: e.target.value }))}>
              <option value="">All</option>
              <option value="true">With Phone</option>
              <option value="false">Without Phone</option>
            </select>
          </div>
          <div className="filter-group">
            <label>Sort</label>
            <select value={filters.sort} onChange={e => setFilters(f => ({ ...f, sort: e.target.value }))}>
              <option value="newest">Newest First</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
          </div>
        </div>
        <div className="filter-actions">
          <button className="btn btn-primary" onClick={() => fetchListings(0)} disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
          <button className="btn btn-outline" onClick={() => { setFilters(defaultFilters); setSearchPhone('') }}>
            Reset
          </button>
        </div>
      </div>

      <div className="phone-search">
        <input
          type="text" placeholder="Search by phone number (e.g. 0712345678)"
          value={searchPhone}
          onChange={e => setSearchPhone(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearchPhone()}
        />
        <button className="btn btn-primary" onClick={handleSearchPhone}>Search Phone</button>
      </div>

      <div className="results-info">
        <span>{totalCount} results{loading && ' (loading...)'}</span>
        {totalPages > 1 && (
          <div className="pagination">
            <button disabled={currentPage <= 1} onClick={() => fetchListings(0)}>First</button>
            <button disabled={currentPage <= 1} onClick={() => fetchListings(offset - limit)}>Prev</button>
            <span>Page {currentPage} of {totalPages}</span>
            <button disabled={currentPage >= totalPages} onClick={() => fetchListings(offset + limit)}>Next</button>
            <button disabled={currentPage >= totalPages} onClick={() => fetchListings((totalPages - 1) * limit)}>Last</button>
          </div>
        )}
      </div>

      <div className="listings">
        {listings.map(listing => (
          <div key={listing.id} className="listing-card">
            <div className="card-header">
              <div className="card-title">
                <h3>{listing.title || 'Untitled'}</h3>
                <div className="card-meta">
                  {listing.platform_name && <Badge label={listing.platform_name} color="blue" />}
                  {listing.listing_type && <Badge label={listing.listing_type} color={listing.listing_type === 'sale' ? 'green' : 'orange'} />}
                  {listing.location && <Badge label={listing.location} color="purple" />}

                </div>
              </div>
              <div className="card-price">
                {formatPrice(listing.price_amount, listing.price_currency, listing.price_period)}
              </div>
            </div>
            <div className="card-body">
              <div className="card-details">
                {listing.bedrooms !== null && <span>{listing.bedrooms} bed</span>}
                {listing.bathrooms !== null && <span>{listing.bathrooms} bath</span>}
                {listing.size_value !== null && <span>{listing.size_value} {listing.size_unit || 'sqm'}</span>}
                {listing.location_text && <span className="location">{listing.location_text}</span>}
              </div>
              {listing.description && <p className="description">{listing.description.slice(0, 200)}{(listing.description.length > 200) ? '...' : ''}</p>}
              <div className="card-agent">
                <div>
                  {listing.agency_name && <span>Agent: {listing.agency_name}</span>}
                  {listing.agent_name && <span>{listing.agent_name}</span>}
                  {listing.agency_url && <a href={listing.agency_url} target="_blank" rel="noopener noreferrer">Agency site</a>}
                </div>
                <div className="card-actions">
                  <a href={listing.source_url} target="_blank" rel="noopener noreferrer" className="btn-view">View Property</a>
                  {listing.phone_numbers.length > 0 && (
                    <button className="btn-wa" onClick={() => setContactListing(listing)}>Contact Agent</button>
                  )}
                </div>
              </div>
              <div className="card-date">{formatDate(listing.date_posted)}</div>
            </div>
            <div className="card-footer">
              <button className="btn btn-small" onClick={() => setExpandedId(expandedId === listing.id ? null : listing.id)}>
                {expandedId === listing.id ? 'Hide Contacts' : 'Show Contacts'}
              </button>
            </div>
            {expandedId === listing.id && (
              <div className="card-contacts">
                <h4>Contact Information</h4>
                <div className="contacts-grid">
                  <div className="contact-field">
                    <span className="contact-label">Phone / WhatsApp</span>
                    <span className="contact-value">
                      {listing.phone_numbers.length > 0
                        ? listing.phone_numbers.map((p, i) => (
                          <span key={i}><a href={waLink(p)} target="_blank" rel="noopener noreferrer">{p}</a>{i < listing.phone_numbers.length - 1 ? ', ' : ''}</span>
                        ))
                        : listing.whatsapp_numbers.length > 0
                        ? listing.whatsapp_numbers.map((p, i) => (
                          <span key={i}><a href={waLink(p)} target="_blank" rel="noopener noreferrer">{p}</a>{i < listing.whatsapp_numbers.length - 1 ? ', ' : ''}</span>
                        ))
                        : 'Not available'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
        {!loading && listings.length === 0 && (
          <div className="empty">No listings found. Try adjusting your filters.</div>
        )}
      </div>

      {contactListing && (
        <div className="modal-overlay" onClick={() => setContactListing(null)}>
          <div className="modal-dialog" onClick={e => e.stopPropagation()}>
            <h4>Contact Agent</h4>
            <textarea
              className="modal-message"
              rows={4}
              value={composeMessage(contactListing)}
              readOnly
            />
            <div className="modal-actions">
              <button className="btn btn-outline" onClick={() => setContactListing(null)}>Cancel</button>
              <a
                href={waMsgLink(contactListing.phone_numbers[0], composeMessage(contactListing))}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
              >Send Message</a>
            </div>
          </div>
        </div>
      )}

      {/* Agent Eve Chat */}
      <button className="chat-toggle" onClick={() => setChatOpen(o => !o)}>
        {chatOpen ? '✕' : '💬'}
      </button>

      {chatOpen && (
        <div className="chat-panel">
          <div className="chat-header">
            <span className="chat-header-name">Agent Eve</span>
            <span className="chat-header-sub">Property Assistant</span>
          </div>
          <div className="chat-body">
            {chatMessages.map((m, i) => (
              <div key={i} className={`chat-msg chat-msg-${m.role}`}>
                {m.content}
              </div>
            ))}
            {chatLoading && <div className="chat-msg chat-msg-assistant chat-msg-typing">...</div>}
            <div ref={chatEndRef} />
          </div>
          <div className="chat-footer">
            <input
              type="text"
              placeholder="Ask me about properties..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleChatSend()}
              disabled={chatLoading}
            />
            <button className="btn btn-primary" onClick={handleChatSend} disabled={chatLoading || !chatInput.trim()}>
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
