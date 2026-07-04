import { Filters } from '../utils/formatting'

interface FiltersPanelProps {
  filters: Filters
  setFilters: (filters: Filters) => void
  platforms: { id: string; name: string }[]
  onSearch: () => void
  onReset: () => void
  loading?: boolean
}

export default function FiltersPanel({ filters, setFilters, platforms, onSearch, onReset, loading }: FiltersPanelProps) {
  return (
    <div className="filters">
      <div className="filter-grid">
        <div className="filter-group">
          <label>Type</label>
          <select value={filters.listing_type} onChange={e => setFilters({ ...filters, listing_type: e.target.value })}>
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
            onChange={e => setFilters({ ...filters, location: e.target.value })}
          />
        </div>
        <div className="filter-group">
          <label>Min Price (KES)</label>
          <input
            type="number" placeholder="0"
            value={filters.min_price}
            onChange={e => setFilters({ ...filters, min_price: e.target.value })}
          />
        </div>
        <div className="filter-group">
          <label>Max Price (KES)</label>
          <input
            type="number" placeholder="10000000"
            value={filters.max_price}
            onChange={e => setFilters({ ...filters, max_price: e.target.value })}
          />
        </div>
        <div className="filter-group">
          <label>Bedrooms</label>
          <select value={filters.min_bedrooms} onChange={e => setFilters({ ...filters, min_bedrooms: e.target.value })}>
            <option value="">Any</option>
            {[1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n}+</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Platform</label>
          <select value={filters.platform} onChange={e => setFilters({ ...filters, platform: e.target.value })}>
            <option value="">All</option>
            {platforms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Has Phone</label>
          <select value={filters.has_phone} onChange={e => setFilters({ ...filters, has_phone: e.target.value })}>
            <option value="">All</option>
            <option value="true">With Phone</option>
            <option value="false">Without Phone</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Sort</label>
          <select value={filters.sort} onChange={e => setFilters({ ...filters, sort: e.target.value })}>
            <option value="newest">Newest First</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
          </select>
        </div>
      </div>
      <div className="filter-actions">
        <button className="btn btn-primary" onClick={onSearch} disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
        <button className="btn btn-outline" onClick={onReset}>
          Reset
        </button>
      </div>
    </div>
  )
}