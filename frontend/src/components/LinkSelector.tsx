import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { Policy, Event, Risk } from '@/api/types'
import { Plus, X, Search } from 'lucide-react'

interface LinkSelectorProps {
  type: 'policy' | 'event' | 'risk'
  selectedIds: string[]
  onChange: (ids: string[]) => void
  excludeId?: string
}

export function LinkSelector({ type, selectedIds, onChange, excludeId }: LinkSelectorProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  const { data: policies } = useQuery({
    queryKey: ['policies'],
    queryFn: () => api<Policy[]>('/policies'),
    enabled: type === 'policy' && open,
  })
  const { data: events } = useQuery({
    queryKey: ['events'],
    queryFn: () => api<Event[]>('/events'),
    enabled: type === 'event' && open,
  })
  const { data: risks } = useQuery({
    queryKey: ['risks'],
    queryFn: () => api<Risk[]>('/risks'),
    enabled: type === 'risk' && open,
  })

  const items: Array<{ id: string; label: string; sublabel: string }> = (() => {
    if (type === 'policy') return (policies || []).map(p => ({ id: p.id, label: p.title, sublabel: p.domain.replace(/_/g, ' ') }))
    if (type === 'event') return (events || []).map(e => ({ id: e.id, label: `${e.reference}: ${e.title}`, sublabel: e.status }))
    if (type === 'risk') return (risks || []).map(r => ({ id: r.id, label: `${r.reference}: ${r.title}`, sublabel: `Score: ${r.risk_score}` }))
    return []
  })()

  const filtered = items
    .filter(i => i.id !== excludeId)
    .filter(i => !selectedIds.includes(i.id))
    .filter(i => !search || i.label.toLowerCase().includes(search.toLowerCase()))

  const typeLabel = type === 'policy' ? 'Policy' : type === 'event' ? 'Event' : 'Risk'

  // Only show the "add" control — selected items are rendered by the parent
  return (
    <div>
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-1 text-sm text-sgmc-600 hover:text-sgmc-800"
        >
          <Plus className="w-3.5 h-3.5" /> Link {typeLabel}
        </button>
      ) : (
        <div className="border rounded-lg shadow-sm bg-white">
          <div className="flex items-center gap-2 px-3 py-2 border-b">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              className="flex-1 text-sm outline-none"
              placeholder={`Search ${typeLabel.toLowerCase()}s...`}
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoFocus
            />
            <button onClick={() => { setOpen(false); setSearch('') }} className="text-gray-400 hover:text-gray-600">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="max-h-48 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="text-sm text-gray-500 p-3">No {typeLabel.toLowerCase()}s to link</p>
            ) : (
              filtered.slice(0, 20).map(item => (
                <button
                  key={item.id}
                  onClick={() => { onChange([...selectedIds, item.id]); setOpen(false); setSearch('') }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 border-b last:border-0"
                >
                  <p className="font-medium truncate">{item.label}</p>
                  <p className="text-xs text-gray-500">{item.sublabel}</p>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
