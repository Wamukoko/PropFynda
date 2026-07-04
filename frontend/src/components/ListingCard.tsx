import { Listing } from '../utils/formatting'
import Badge from './Badge'
import { formatPrice, formatDate, waLink, composeMessage, waMsgLink } from '../utils/formatting'

interface ListingCardProps {
  listing: Listing
  onContact: (listing: Listing) => void
  expandedId: number | null
  setExpandedId: (id: number | null) => void
}

export default function ListingCard({ listing, onContact, expandedId, setExpandedId }: ListingCardProps) {
  return (
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
              <button className="btn-wa" onClick={() => onContact(listing)}>Contact Agent</button>
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
  )
}