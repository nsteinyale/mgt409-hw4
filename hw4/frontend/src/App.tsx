import { Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import ChatWidget from './components/ChatWidget'
import HarvardChase from './components/HarvardChase'
import OfflineBanner from './components/OfflineBanner'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductPage from './pages/ProductPage'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'
import Play from './pages/Play'
import NotFound from './pages/NotFound'

export default function App() {
  const { pathname } = useLocation()
  return (
    <div className="app">
      <OfflineBanner />
      <NavBar />
      <main className="main">
        {/* key: each new page fades in */}
        <div key={pathname} className="page-fade">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:productId" element={<ProductPage />} />
            <Route path="/about" element={<About />} />
            <Route path="/login" element={<Login />} />
            <Route path="/create-account" element={<CreateAccount />} />
            <Route path="/play" element={<Play />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </main>
      <Footer />
      <HarvardChase />
      <ChatWidget />
    </div>
  )
}
