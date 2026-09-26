import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Package,
  Warehouse,
  ArrowDownLeft,
  ArrowUpRight,
  ArrowLeftRight,
  SlidersHorizontal,
  Tags,
  BarChart3,
  LogOut,
  Plus,
  RefreshCw,
  Search,
  AlertTriangle,
  CheckCircle2,
  Clock,
  User,
  ShieldCheck,
} from 'lucide-react';
import { apiFetch, getAuthToken, setAuthToken } from './api';

export default function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(getAuthToken());
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Auth Form State
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register' | 'forgot'
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authName, setAuthName] = useState('');
  const [authOtp, setAuthOtp] = useState('');
  const [authMsg, setAuthMsg] = useState('');

  // Dashboard Data
  const [kpis, setKpis] = useState(null);
  const [recentDocs, setRecentDocs] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  
  // Products Data
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [adjustments, setAdjustments] = useState([]);

  // New Item Modals
  const [showProductModal, setShowProductModal] = useState(false);
  const [newProduct, setNewProduct] = useState({ name: '', sku: '', category_id: '', unit_of_measure: 'pcs', reorder_level: 10, description: '' });

  useEffect(() => {
    if (token) {
      loadInitialData();
    }
  }, [token]);

  const loadInitialData = async () => {
    try {
      const kpiRes = await apiFetch('/dashboard/kpis');
      setKpis(kpiRes);
      
      const recentRes = await apiFetch('/dashboard/recent-operations');
      setRecentDocs(recentRes);

      const lowRes = await apiFetch('/dashboard/low-stock-alerts');
      setLowStock(lowRes);

      const prodRes = await apiFetch('/products/');
      setProducts(prodRes);

      const catRes = await apiFetch('/categories/');
      setCategories(catRes);

      const whRes = await apiFetch('/warehouses/');
      setWarehouses(whRes);

      const recRes = await apiFetch('/receipts/');
      setReceipts(recRes);

      const delRes = await apiFetch('/deliveries/');
      setDeliveries(delRes);

      const trnRes = await apiFetch('/transfers/');
      setTransfers(trnRes);

      const adjRes = await apiFetch('/adjustments/');
      setAdjustments(adjRes);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthMsg('');
    try {
      if (authMode === 'login') {
        const res = await apiFetch('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email: authEmail, password: authPassword }),
        });
        setAuthToken(res.access_token);
        setToken(res.access_token);
        setUser(res.user);
      } else if (authMode === 'register') {
        const res = await apiFetch('/auth/register', {
          method: 'POST',
          body: JSON.stringify({ name: authName, email: authEmail, password: authPassword }),
        });
        setAuthMsg('Account registered successfully! Please log in.');
        setAuthMode('login');
      } else if (authMode === 'forgot') {
        const res = await apiFetch('/auth/forgot-password', {
          method: 'POST',
          body: JSON.stringify({ email: authEmail }),
        });
        setAuthMsg(`OTP sent to ${authEmail}: ${res.otp_demo}`);
      }
    } catch (err) {
      setAuthMsg(err.message);
    }
  };

  const handleLogout = () => {
    setAuthToken(null);
    setToken(null);
    setUser(null);
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    try {
      await apiFetch('/products/', {
        method: 'POST',
        body: JSON.stringify(newProduct),
      });
      setShowProductModal(false);
      loadInitialData();
    } catch (err) {
      alert(err.message);
    }
  };

  if (!token) {
    return (
      <div className="auth-wrapper">
        <div className="glass-card auth-card">
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <div className="sidebar-logo-icon" style={{ margin: '0 auto 1rem auto', width: '48px', height: '48px' }}>
              <Package size={28} />
            </div>
            <h1 className="sidebar-logo-text" style={{ fontSize: '1.8rem' }}>StockSense</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
              Intelligent Inventory Operations Suite
            </p>
          </div>

          {authMsg && (
            <div style={{ padding: '0.75rem', borderRadius: '8px', background: 'rgba(99,102,241,0.15)', color: '#a5b4fc', fontSize: '0.85rem', marginBottom: '1rem', border: '1px solid rgba(99,102,241,0.3)' }}>
              {authMsg}
            </div>
          )}

          <form onSubmit={handleAuthSubmit}>
            {authMode === 'register' && (
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="John Doe"
                  value={authName}
                  onChange={(e) => setAuthName(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                className="form-input"
                placeholder="manager@stocksense.com"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
              />
            </div>

            {authMode !== 'forgot' && (
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="••••••••"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  required
                />
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem' }}>
              {authMode === 'login' ? 'Sign In to Dashboard' : authMode === 'register' ? 'Create Account' : 'Send Reset Link'}
            </button>
          </form>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.25rem', fontSize: '0.85rem' }}>
            {authMode === 'login' ? (
              <>
                <a href="#" style={{ color: 'var(--text-muted)' }} onClick={() => setAuthMode('register')}>Create account</a>
                <a href="#" style={{ color: 'var(--accent-indigo)' }} onClick={() => setAuthMode('forgot')}>Forgot password?</a>
              </>
            ) : (
              <a href="#" style={{ color: 'var(--accent-indigo)' }} onClick={() => setAuthMode('login')}>Back to login</a>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <Package size={22} />
          </div>
          <span className="sidebar-logo-text">StockSense</span>
        </div>

        <nav className="sidebar-nav">
          <button className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </button>
          <button className={`nav-item ${activeTab === 'products' ? 'active' : ''}`} onClick={() => setActiveTab('products')}>
            <Package size={18} />
            <span>Products</span>
          </button>
          <button className={`nav-item ${activeTab === 'receipts' ? 'active' : ''}`} onClick={() => setActiveTab('receipts')}>
            <ArrowDownLeft size={18} />
            <span>Receipts</span>
          </button>
          <button className={`nav-item ${activeTab === 'deliveries' ? 'active' : ''}`} onClick={() => setActiveTab('deliveries')}>
            <ArrowUpRight size={18} />
            <span>Deliveries</span>
          </button>
          <button className={`nav-item ${activeTab === 'transfers' ? 'active' : ''}`} onClick={() => setActiveTab('transfers')}>
            <ArrowLeftRight size={18} />
            <span>Transfers</span>
          </button>
          <button className={`nav-item ${activeTab === 'adjustments' ? 'active' : ''}`} onClick={() => setActiveTab('adjustments')}>
            <SlidersHorizontal size={18} />
            <span>Adjustments</span>
          </button>
          <button className={`nav-item ${activeTab === 'warehouses' ? 'active' : ''}`} onClick={() => setActiveTab('warehouses')}>
            <Warehouse size={18} />
            <span>Warehouses</span>
          </button>
          <button className={`nav-item ${activeTab === 'categories' ? 'active' : ''}`} onClick={() => setActiveTab('categories')}>
            <Tags size={18} />
            <span>Categories</span>
          </button>
          <button className={`nav-item ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
            <BarChart3 size={18} />
            <span>Analytics & Reports</span>
          </button>
        </nav>

        <button className="nav-item" style={{ marginTop: 'auto', color: '#f43f5e' }} onClick={handleLogout}>
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </aside>

      {/* Main App Content Area */}
      <main className="main-content">
        <header className="topbar">
          <h2 className="page-title">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Overview</h2>

          <div className="user-profile">
            <button className="btn btn-secondary" onClick={loadInitialData}>
              <RefreshCw size={16} /> Sync
            </button>
            <div className="avatar">A</div>
          </div>
        </header>

        <div style={{ padding: '2rem' }}>
          {/* DASHBOARD TAB */}
          {activeTab === 'dashboard' && (
            <>
              <div className="kpi-grid">
                <div className="glass-card kpi-card">
                  <div className="kpi-icon indigo"><Package size={24} /></div>
                  <div>
                    <div className="kpi-value">{kpis?.total_products || 0}</div>
                    <div className="kpi-label">Total Products</div>
                  </div>
                </div>

                <div className="glass-card kpi-card">
                  <div className="kpi-icon rose"><AlertTriangle size={24} /></div>
                  <div>
                    <div className="kpi-value">{kpis?.low_stock_count || 0}</div>
                    <div className="kpi-label">Low / Out of Stock</div>
                  </div>
                </div>

                <div className="glass-card kpi-card">
                  <div className="kpi-icon amber"><Clock size={24} /></div>
                  <div>
                    <div className="kpi-value">{kpis?.pending_receipts || 0}</div>
                    <div className="kpi-label">Pending Receipts</div>
                  </div>
                </div>

                <div className="glass-card kpi-card">
                  <div className="kpi-icon cyan"><ArrowUpRight size={24} /></div>
                  <div>
                    <div className="kpi-value">{kpis?.pending_deliveries || 0}</div>
                    <div className="kpi-label">Pending Deliveries</div>
                  </div>
                </div>

                <div className="glass-card kpi-card">
                  <div className="kpi-icon emerald"><ArrowLeftRight size={24} /></div>
                  <div>
                    <div className="kpi-value">{kpis?.scheduled_transfers || 0}</div>
                    <div className="kpi-label">Scheduled Transfers</div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Recent Operations Stream</h3>
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Doc Reference</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentDocs.map((doc, i) => (
                        <tr key={i}>
                          <td style={{ fontWeight: 600 }}>{doc.doc_number}</td>
                          <td>{doc.type}</td>
                          <td><span className={`badge badge-${doc.status.toLowerCase()}`}>{doc.status}</span></td>
                          <td style={{ color: 'var(--text-muted)' }}>{doc.date ? new Date(doc.date).toLocaleDateString() : 'Today'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f43f5e' }}>Low Stock Alerts</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {lowStock.map((item, i) => (
                      <div key={i} style={{ padding: '0.75rem', background: 'rgba(244,63,94,0.1)', borderRadius: '10px', border: '1px solid rgba(244,63,94,0.2)' }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{item.name} ({item.sku})</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                          Stock: <span style={{ color: '#fb7185', fontWeight: 700 }}>{item.total_stock}</span> / Reorder: {item.reorder_level}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}

          {/* PRODUCTS TAB */}
          {activeTab === 'products' && (
            <div className="glass-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3>Product Master Registry</h3>
                <button className="btn btn-primary" onClick={() => setShowProductModal(true)}>
                  <Plus size={16} /> Add Product
                </button>
              </div>

              <table className="custom-table">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Unit</th>
                    <th>Reorder Threshold</th>
                    <th>Stock On Hand</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 600, color: 'var(--accent-indigo)' }}>{p.sku}</td>
                      <td style={{ fontWeight: 600 }}>{p.name}</td>
                      <td>{p.category_name || 'Uncategorized'}</td>
                      <td>{p.unit_of_measure}</td>
                      <td>{p.reorder_level}</td>
                      <td style={{ fontWeight: 700, color: p.total_stock <= p.reorder_level ? '#fb7185' : '#34d399' }}>
                        {p.total_stock}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* RECEIPTS TAB */}
          {activeTab === 'receipts' && (
            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem' }}>Goods Receipts (Incoming Stock)</h3>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Receipt #</th>
                    <th>Supplier</th>
                    <th>Warehouse</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {receipts.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.receipt_number}</td>
                      <td>{r.supplier}</td>
                      <td>{r.warehouse_id}</td>
                      <td><span className={`badge badge-${r.status.toLowerCase()}`}>{r.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* DELIVERIES TAB */}
          {activeTab === 'deliveries' && (
            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem' }}>Delivery Orders (Outgoing Stock)</h3>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Delivery #</th>
                    <th>Customer</th>
                    <th>Warehouse</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {deliveries.map((d) => (
                    <tr key={d.id}>
                      <td style={{ fontWeight: 600 }}>{d.delivery_number}</td>
                      <td>{d.customer}</td>
                      <td>{d.warehouse_id}</td>
                      <td><span className={`badge badge-${d.status.toLowerCase()}`}>{d.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TRANSFERS TAB */}
          {activeTab === 'transfers' && (
            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem' }}>Internal Stock Transfers</h3>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Transfer #</th>
                    <th>From Location</th>
                    <th>To Location</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.map((t) => (
                    <tr key={t.id}>
                      <td style={{ fontWeight: 600 }}>{t.transfer_number}</td>
                      <td>{t.from_location_id}</td>
                      <td>{t.to_location_id}</td>
                      <td><span className={`badge badge-${t.status.toLowerCase()}`}>{t.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ADJUSTMENTS TAB */}
          {activeTab === 'adjustments' && (
            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem' }}>Inventory Physical Counts & Adjustments</h3>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Adjustment #</th>
                    <th>Location</th>
                    <th>Reason</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {adjustments.map((a) => (
                    <tr key={a.id}>
                      <td style={{ fontWeight: 600 }}>{a.adjustment_number}</td>
                      <td>{a.location_id}</td>
                      <td>{a.reason}</td>
                      <td><span className={`badge badge-${a.status.toLowerCase()}`}>{a.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* WAREHOUSES TAB */}
          {activeTab === 'warehouses' && (
            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem' }}>Warehouse Infrastructure</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginTop: '1rem' }}>
                {warehouses.map((w) => (
                  <div key={w.id} className="glass-card" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                      <Warehouse size={20} color="var(--accent-indigo)" />
                      <h4 style={{ fontSize: '1.1rem' }}>{w.name}</h4>
                    </div>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Code: {w.code}</p>
                    <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', marginTop: '4px' }}>{w.address || 'Main Logistics Facility'}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CATEGORIES TAB */}
          {activeTab === 'categories' && (
            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem' }}>Product Categories</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                {categories.map((c) => (
                  <div key={c.id} className="glass-card" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <Tags size={18} color="var(--accent-purple)" />
                    <h4 style={{ marginTop: '0.5rem' }}>{c.name}</h4>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '4px' }}>{c.description || 'General category'}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* REPORTS TAB */}
          {activeTab === 'reports' && (
            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem' }}>Valuation & Inventory Movement Reports</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Comprehensive breakdown of total asset valuation and stock velocity metrics.</p>
              <div className="kpi-grid">
                <div className="glass-card kpi-card">
                  <div className="kpi-icon emerald"><BarChart3 size={24} /></div>
                  <div>
                    <div className="kpi-value">$124,500.00</div>
                    <div className="kpi-label">Total Asset Value</div>
                  </div>
                </div>
                <div className="glass-card kpi-card">
                  <div className="kpi-icon indigo"><RefreshCw size={24} /></div>
                  <div>
                    <div className="kpi-value">4.2x</div>
                    <div className="kpi-label">Inventory Turnover Rate</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* CREATE PRODUCT MODAL */}
      {showProductModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: '500px' }}>
            <h3 style={{ marginBottom: '1.25rem' }}>Register New Product</h3>
            <form onSubmit={handleCreateProduct}>
              <div className="form-group">
                <label>Product Name</label>
                <input type="text" className="form-input" required value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>SKU Code</label>
                <input type="text" className="form-input" required value={newProduct.sku} onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Unit of Measure</label>
                <input type="text" className="form-input" required value={newProduct.unit_of_measure} onChange={(e) => setNewProduct({ ...newProduct, unit_of_measure: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Reorder Threshold Level</label>
                <input type="number" className="form-input" value={newProduct.reorder_level} onChange={(e) => setNewProduct({ ...newProduct, reorder_level: parseFloat(e.target.value) })} />
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setShowProductModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Save Product</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
