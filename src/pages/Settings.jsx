import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'

const CURRENCIES = ['EUR', 'GBP', 'USD', 'CHF', 'NOK', 'SEK', 'DKK']
const VAT_MODES  = [
  { value: 'excluded', label: 'Ex-VAT (add VAT on top)' },
  { value: 'included', label: 'Inc-VAT (VAT already in price)' },
]
const ROUND_OPTIONS = [
  { value: 0,    label: 'No rounding' },
  { value: 10,   label: 'Round up to nearest €10' },
  { value: 50,   label: 'Round up to nearest €50' },
  { value: 100,  label: 'Round up to nearest €100' },
  { value: 500,  label: 'Round up to nearest €500' },
  { value: 1000, label: 'Round up to nearest €1,000' },
]

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {hint && <p className="text-xs text-gray-400 mb-1.5">{hint}</p>}
      {children}
    </div>
  )
}

function NumberInput({ value, onChange, min, max, step = 0.1, suffix }) {
  return (
    <div className="relative w-48">
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={e => onChange(parseFloat(e.target.value) || 0)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
      />
      {suffix && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">{suffix}</span>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const [form, setForm]     = useState(null)
  const [saved, setSaved]   = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState(null)

  useEffect(() => {
    apiFetch('/settings')
      .then(d => setForm(d))
      .catch(e => setError(e.message))
  }, [])

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await apiFetch('/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      setForm(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (error) return (
    <div className="p-8 text-red-600 text-sm">Error: {error}</div>
  )
  if (!form) return (
    <div className="p-8 text-gray-400 text-sm">Loading…</div>
  )

  const exampleCost     = 10000
  const markupAmt       = exampleCost * form.default_markup_percent / 100
  const exVat           = exampleCost + markupAmt
  const vatAmt          = exVat * form.vat_rate_percent / 100
  const incVat          = exVat + vatAmt
  const rounded         = form.round_to_nearest > 0
    ? Math.ceil(incVat / form.round_to_nearest) * form.round_to_nearest
    : incVat
  const fmt = n => n.toLocaleString('en-IE', { style: 'currency', currency: form.currency, maximumFractionDigits: 0 })

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Manufacturer Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Pricing defaults applied to all pod quotes. Individual quotes can override markup at spec level.</p>
      </div>

      <div className="bg-white border border-gray-100 rounded-xl divide-y divide-gray-100">

        {/* ── Pricing ── */}
        <div className="px-6 py-5 space-y-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Pricing</div>

          <Field label="Default markup" hint="Applied to internal material + build-up cost to arrive at selling price.">
            <NumberInput
              value={form.default_markup_percent}
              onChange={v => set('default_markup_percent', v)}
              min={0} max={500} step={0.5} suffix="%"
            />
          </Field>

          <Field label="Currency">
            <select
              value={form.currency}
              onChange={e => set('currency', e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
        </div>

        {/* ── VAT ── */}
        <div className="px-6 py-5 space-y-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-widest">VAT</div>

          <Field label="VAT rate">
            <NumberInput
              value={form.vat_rate_percent}
              onChange={v => set('vat_rate_percent', v)}
              min={0} max={100} step={0.5} suffix="%"
            />
          </Field>

          <Field label="VAT display mode" hint="How VAT is shown on client quotes.">
            <div className="space-y-2">
              {VAT_MODES.map(m => (
                <label key={m.value} className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="radio"
                    name="vat_mode"
                    value={m.value}
                    checked={form.vat_mode === m.value}
                    onChange={() => set('vat_mode', m.value)}
                    className="accent-blue-600"
                  />
                  <span className="text-sm text-gray-700">{m.label}</span>
                </label>
              ))}
            </div>
          </Field>
        </div>

        {/* ── Rounding ── */}
        <div className="px-6 py-5 space-y-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Rounding</div>

          <Field label="Round quoted price up to nearest" hint="Applied after markup + VAT. Quoted price is always rounded up, never down.">
            <select
              value={form.round_to_nearest}
              onChange={e => set('round_to_nearest', parseInt(e.target.value))}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {ROUND_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
        </div>

        {/* ── Live preview ── */}
        <div className="px-6 py-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">Pricing Preview</div>
          <p className="text-xs text-gray-400 mb-3">Example: {fmt(exampleCost)} internal cost →</p>
          <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            {[
              ['Internal cost',   fmt(exampleCost)],
              [`Markup (${form.default_markup_percent}%)`, fmt(markupAmt)],
              ['Selling ex-VAT',  fmt(exVat)],
              [`VAT (${form.vat_rate_percent}%)`,          fmt(vatAmt)],
              ['Selling inc-VAT', fmt(incVat)],
              ['Quoted price',    <span key="q" className="font-semibold text-gray-900">{fmt(rounded)}</span>],
            ].map(([k, v]) => (
              <div key={k} className="contents">
                <span className="text-gray-500">{k}</span>
                <span className="text-gray-800">{v}</span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* ── Save bar ── */}
      <div className="mt-5 flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving…' : 'Save settings'}
        </button>
        {saved && <span className="text-sm text-green-600 font-medium">Saved</span>}
        {error && <span className="text-sm text-red-500">{error}</span>}
      </div>
    </div>
  )
}
