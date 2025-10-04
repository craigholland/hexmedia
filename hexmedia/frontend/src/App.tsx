import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import Header from '@/components/Header'
import RouteBoundary from '@/components/RouteBoundary'
import BucketsIndex from '@/routes/BucketsIndex'
import BucketView from '@/routes/BucketView'
import IngestPage from '@/routes/IngestPage'
import ThumbsPage from '@/routes/ThumbsPage'
import ItemDetail from '@/routes/ItemDetail'
import SettingsLayout from '@/routes/settings/SettingsLayout'
import SettingsTags from '@/routes/SettingsTags'
import { ToastProvider } from "@/providers/ToastProvider";

const qc = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <div className="min-h-screen bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
          <Header />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
              <ToastProvider>
              <RouteBoundary>
            <Routes>
              <Route path="/" element={<Navigate to="/buckets" replace />} />
              <Route path="/buckets" element={<BucketsIndex />} />
              <Route path="/bucket/:bucket" element={<BucketView />} />
                 <Route path="/bucket/:bucket/item/:id" element={<ItemDetail />} />
              <Route path="/tools/ingest" element={<IngestPage />} />
              <Route path="/tools/thumbs" element={<ThumbsPage />} />
                <Route path="/settings" element={<SettingsLayout />}>
                  <Route path="tags" element={<SettingsTags />} />
                </Route>
              <Route path="*" element={<div>Not Found</div>} />
            </Routes>
              </RouteBoundary>
                  </ToastProvider>
          </main>
        </div>
      </BrowserRouter>
        <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
    </QueryClientProvider>
  )
}
