import { useState, useEffect, useRef } from 'react'
import './App.css'
import { useListings } from './hooks/useListings'
import { useChat } from './hooks/useChat'
import FiltersPanel from './components/FiltersPanel'
import ListingCard from './components/ListingCard'
import ChatPanel from './components/ChatPanel'
import { formatPrice, formatDate, waLink, composeMessage, waMsgLink } from './utils/formatting'

const defaultFilters = {
  listing_type: '',
  location: '',
  min_price: '',
  max_price: '',
  min_bedrooms: '',
  platform: '',
  has_phone: '',
  sort: 'newest',
}

export default function App() {
  const [contactListing, setContactListing] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const searchPhoneInputRef = useRef(null)

  const { listings, totalCount, platforms, filters, setFilters, offset, loading, totalPages, currentPage, fetchListings, searchByPhone } = useListings(defaultFilters)
  const { chatMessages, chatInput, setChatInput, chatLoading, chatEndRef, sendMessage } = useChat()

  const handleSearchPhone = () => {
    const phone = searchPhoneInputRef.current?.value
    if (!phone?.trim()) return
    searchByPhone(phone)
  }

  const handleChatSend = () => {
    sendMessage()
  }

  const resetFilters = () => {
    setFilters(defaultFilters)
    if (searchPhoneInputRef.current) searchPhoneInputRef.current.value = ''
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Kenya Property Listings</h1>
        <p className="subtitle">{totalCount} listings across {platforms.length} platforms</p>
      </header>

      <FiltersPanel
        filters={filters}
        setFilters={setFilters}
        platforms={platforms}
        onSearch={() => fetchListings(0)}
        onReset={resetFilters}
        loading={loading}
      />

      <div className="phone-search">
        <input
          type="text" placeholder="Search by phone number (e.g. 0712345678)"
          ref={searchPhoneInputRef}
          onKeyDown={e => e.key === 'Enter' && handleSearchPhone()}
        />
        <button className="btn btn-primary" onClick={handleSearchPhone}>Search Phone</button>
      </div>

      <div className="results-info">
        <span>{totalCount} results{loading && ' (loading...)'}</span>
        {totalPages > 1 && (
          <div className="pagination">
            <button disabled={currentPage <= 1} onClick={() => fetchListings(0)}>First</button>
            <button disabled={currentPage <= 1} onClick={() => fetchListings(offset - 25)}>Prev</button>
            <span>Page {currentPage} of {totalPages}</span>
            <button disabled={currentPage >= totalPages} onClick={() => fetchListings(offset + 25)}>Next</button>
            <button disabled={currentPage >= totalPages} onClick={() => fetchListings((totalPages - 1) * 25)}>Last</button>
          </div>
        )}
      </div>

      <div className="listings">
        {listings.map(listing => (
          <ListingCard
            key={listing.id}
            listing={listing}
            onContact={setContactListing}
            expandedId={expandedId}
            setExpandedId={setExpandedId}
          />
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

      <button className="chat-toggle" onClick={() => setChatOpen(o => !o)}>
        {chatOpen ? '✕' : '💬'}
      </button>

      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        initialMessages={chatMessages}
      />
    </div>
  )
}
