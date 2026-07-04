import { useState, useCallback, useEffect } from 'react'
import { fetchListings, fetchPlatforms, searchByPhone } from '../utils/api'
import { Filters } from '../utils/formatting'

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

export function useListings(initialFilters: Filters) {
  const [listings, setListings] = useState<Listing[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [platforms, setPlatforms] = useState<Platform[]>([])
  const [filters, setFilters] = useState<Filters>(initialFilters)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const limit = 25

  const fetchListingsCallback = useCallback(async (ofs: number) => {
    setLoading(true)
    try {
      const data = await fetchListings(filters, ofs, limit)
      setListings(data.items)
      setTotalCount(data.total_count)
      setOffset(ofs)
    } catch { /* ignore */ }
    setLoading(false)
  }, [filters])

  const handleSearchPhone = async (phone: string) => {
    if (!phone.trim()) return
    setLoading(true)
    try {
      const data = await searchByPhone(phone.trim(), limit)
      setListings(data.items)
      setTotalCount(data.total_count)
      setOffset(0)
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => {
    fetchPlatforms().then(setPlatforms).catch(() => {})
    fetchListingsCallback(0)
  }, [fetchListingsCallback])

  const totalPages = Math.ceil(totalCount / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return {
    listings,
    totalCount,
    platforms,
    filters,
    setFilters,
    offset,
    loading,
    totalPages,
    currentPage,
    fetchListings: fetchListingsCallback,
    searchByPhone: handleSearchPhone,
  }
}