import { useState, useEffect } from 'react'
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import PodDesigner from './components/PodDesigner'
import Orders from './components/Orders'
import Production from './components/Production'
import Inventory from './components/Inventory'
import Schedule from './components/Schedule'
import BuildUpEditor from './pages/BuildUpEditor'
import MaterialLibraryPage from './pages/MaterialLibrary'
import FinishCataloguePage from './pages/FinishCatalogue'
import SettingsPage from './pages/Settings'
import QuotesPage from './pages/Quotes'
import SuppliersPage from './pages/Suppliers'
import SupplierRespond from './pages/SupplierRespond'
import { apiFetch } from './api/client'

export default function App() {
  // Public route — no auth required
  if (window.location.pathname.startsWith('/rfq-respond/')) {
    return <SupplierRespond />
  }
  const [page, setPage] = useState('dashboard')
  const [warming, setWarming] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setWarming(true), 2000)
    apiFetch('/ping').finally(() => {
      clearTimeout(t)
      setWarming(false)
    })
  }, [])

  const pages = {
    dashboard:        <Dashboard />,
    designer:         <PodDesigner />,
    build_ups:        <BuildUpEditor />,
    materials:        <MaterialLibraryPage />,
    finish_catalogue: <FinishCataloguePage />,
    quotes:           <QuotesPage />,
    suppliers:        <SuppliersPage />,
    orders:           <Orders />,
    production:       <Production />,
    inventory:        <Inventory />,
    schedule:         <Schedule />,
    settings:         <SettingsPage />,
  }

  return (
    <>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
      <SignedIn>
        {warming && (
          <div className="fixed top-0 inset-x-0 z-50 bg-amber-50 border-b border-amber-200 text-amber-700 text-xs text-center py-2 px-4">
            Preparing backend connection — first load may take around 10–20 seconds.
          </div>
        )}
        <div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden">
          <Sidebar page={page} setPage={setPage} />
          <main className="flex-1 overflow-y-auto">
            {pages[page]}
          </main>
        </div>
      </SignedIn>
    </>
  )
}
