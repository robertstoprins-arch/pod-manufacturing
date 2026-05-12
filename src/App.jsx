import { useState } from 'react'
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

export default function App() {
  const [page, setPage] = useState('dashboard')

  const pages = {
    dashboard:        <Dashboard />,
    designer:         <PodDesigner />,
    build_ups:        <BuildUpEditor />,
    materials:        <MaterialLibraryPage />,
    finish_catalogue: <FinishCataloguePage />,
    quotes:           <QuotesPage />,
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
