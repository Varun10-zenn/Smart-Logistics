import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShoppingBag,
  MapPin,
  Plus,
  Minus,
  Trash2,
  Package,
  Store,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  LogOut,
  Clock
} from 'lucide-react';
import { shopApi, type ShopProductItem, type CheckoutItem } from '../api/shopApi';
import { useAuth } from '../contexts/AuthContext';

interface CartItem extends ShopProductItem {
  cartQuantity: number;
}

const DEFAULT_LAT = 12.97;
const DEFAULT_LON = 79.14;

export function ShopPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Location State
  const [lat, setLat] = useState<number>(() => {
    const saved = localStorage.getItem('user_lat');
    return saved ? parseFloat(saved) : DEFAULT_LAT;
  });
  const [lon, setLon] = useState<number>(() => {
    const saved = localStorage.getItem('user_lon');
    return saved ? parseFloat(saved) : DEFAULT_LON;
  });
  const [editingLoc, setEditingLoc] = useState(false);
  const [tempLat, setTempLat] = useState(lat.toString());
  const [tempLon, setTempLon] = useState(lon.toString());
  const [geoLocLoading, setGeoLocLoading] = useState(false);

  // Cart & Checkout State
  const [cart, setCart] = useState<Record<number, CartItem>>({});
  const [address, setAddress] = useState('Katpadi Road, Vellore, Tamil Nadu 632014');
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  // Auto detect location on mount if not saved
  useEffect(() => {
    if (!localStorage.getItem('user_lat') && navigator.geolocation) {
      setGeoLocLoading(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const newLat = parseFloat(pos.coords.latitude.toFixed(4));
          const newLon = parseFloat(pos.coords.longitude.toFixed(4));
          setLat(newLat);
          setLon(newLon);
          localStorage.setItem('user_lat', newLat.toString());
          localStorage.setItem('user_lon', newLon.toString());
          setGeoLocLoading(false);
        },
        () => {
          setGeoLocLoading(false);
        },
        { timeout: 5000 }
      );
    }
  }, []);

  // Fetch shop products for current lat/lon
  const {
    data: shopData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['shop-products', lat, lon],
    queryFn: () => shopApi.getProducts(lat, lon),
    retry: 1,
  });

  const handleApplyManualLocation = (e: React.FormEvent) => {
    e.preventDefault();
    const parsedLat = parseFloat(tempLat);
    const parsedLon = parseFloat(tempLon);
    if (!isNaN(parsedLat) && !isNaN(parsedLon)) {
      setLat(parsedLat);
      setLon(parsedLon);
      localStorage.setItem('user_lat', parsedLat.toString());
      localStorage.setItem('user_lon', parsedLon.toString());
      setEditingLoc(false);
    }
  };

  const handleDetectLocation = () => {
    if (!navigator.geolocation) return;
    setGeoLocLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const newLat = parseFloat(pos.coords.latitude.toFixed(4));
        const newLon = parseFloat(pos.coords.longitude.toFixed(4));
        setLat(newLat);
        setLon(newLon);
        setTempLat(newLat.toString());
        setTempLon(newLon.toString());
        localStorage.setItem('user_lat', newLat.toString());
        localStorage.setItem('user_lon', newLon.toString());
        setGeoLocLoading(false);
        setEditingLoc(false);
      },
      (err) => {
        alert('Geolocation request failed or was denied: ' + err.message);
        setGeoLocLoading(false);
      }
    );
  };

  // Cart operations
  const updateCartQty = (product: ShopProductItem, delta: number) => {
    setCart((prev) => {
      const existing = prev[product.id];
      const currentQty = existing ? existing.cartQuantity : 0;
      const newQty = currentQty + delta;

      if (newQty <= 0) {
        const copy = { ...prev };
        delete copy[product.id];
        return copy;
      }

      if (newQty > product.available_quantity) {
        return prev;
      }

      return {
        ...prev,
        [product.id]: {
          ...product,
          cartQuantity: newQty,
        },
      };
    });
  };

  const removeFromCart = (productId: number) => {
    setCart((prev) => {
      const copy = { ...prev };
      delete copy[productId];
      return copy;
    });
  };

  const cartList = Object.values(cart);
  const totalItemsCount = cartList.reduce((sum, item) => sum + item.cartQuantity, 0);
  const totalPrice = cartList.reduce((sum, item) => sum + item.cartQuantity * item.price, 0);
  const totalWeight = cartList.reduce((sum, item) => sum + item.cartQuantity * item.unit_weight_kg, 0);

  // Checkout Mutation
  const checkoutMutation = useMutation({
    mutationFn: (items: CheckoutItem[]) =>
      shopApi.checkout({
        items,
        lat,
        lon,
        address,
      }),
    onSuccess: (order) => {
      setCart({});
      queryClient.invalidateQueries({ queryKey: ['shop-products'] });
      queryClient.invalidateQueries({ queryKey: ['customer-orders'] });
      navigate(`/shop/orders/${order.id}`);
    },
    onError: (err: any) => {
      console.error(err);
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Checkout failed due to insufficient stock or location conflict.';
      setCheckoutError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      // Refresh inventory stock
      queryClient.invalidateQueries({ queryKey: ['shop-products'] });
    },
  });

  const handleCheckout = () => {
    setCheckoutError(null);
    if (!address.trim()) {
      setCheckoutError('Please enter a valid delivery address.');
      return;
    }
    if (cartList.length === 0) return;

    const checkoutItems: CheckoutItem[] = cartList.map((item) => ({
      product_id: item.id,
      quantity: item.cartQuantity,
    }));

    checkoutMutation.mutate(checkoutItems);
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 font-sans flex flex-col">
      {/* Top Customer Header */}
      <header className="sticky top-0 z-30 bg-[#121824]/90 backdrop-blur-md border-b border-slate-800 px-4 py-3 sm:px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
            <ShoppingBag size={20} />
          </div>
          <div>
            <h1 className="font-serif text-base font-semibold text-white">Meridian Shop</h1>
            <p className="text-[11px] text-slate-400">Hyperlocal Instant Grocery Delivery</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/shop/orders')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-700 bg-slate-800/80 text-xs text-slate-200 hover:bg-slate-700 hover:text-white transition-colors cursor-pointer"
          >
            <Clock size={15} />
            <span>My Orders</span>
          </button>
          {user && (
            <div className="flex items-center gap-2 pl-3 border-l border-slate-800">
              <span className="text-xs text-slate-300 font-medium hidden sm:inline">{user.full_name || user.email}</span>
              <button
                onClick={async () => {
                  await logout();
                  navigate('/login');
                }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                title="Log Out"
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Location & Products */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Location Banner Bar */}
          <div className="p-4 rounded-2xl bg-[#121824] border border-slate-800 space-y-3 shadow-md">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <MapPin size={16} className="text-emerald-400 shrink-0" />
                <span className="font-semibold text-white">Delivery Coordinates:</span>
                <span className="font-mono bg-slate-800/90 px-2 py-0.5 rounded border border-slate-700 text-emerald-300">
                  {lat.toFixed(4)}, {lon.toFixed(4)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleDetectLocation}
                  disabled={geoLocLoading}
                  className="px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <RefreshCw size={13} className={geoLocLoading ? 'animate-spin' : ''} />
                  <span>GPS Detect</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTempLat(lat.toString());
                    setTempLon(lon.toString());
                    setEditingLoc(!editingLoc);
                  }}
                  className="px-2.5 py-1 text-xs bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/30 rounded-lg transition-colors cursor-pointer"
                >
                  {editingLoc ? 'Cancel' : 'Change Location'}
                </button>
              </div>
            </div>

            {/* Manual Lat/Lon Editor */}
            {editingLoc && (
              <form onSubmit={handleApplyManualLocation} className="pt-2 border-t border-slate-800 flex items-center gap-3">
                <div className="flex-1 grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase">Latitude</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={tempLat}
                      onChange={(e) => setTempLat(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase">Longitude</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={tempLon}
                      onChange={(e) => setTempLon(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  className="mt-3 py-1.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Apply
                </button>
              </form>
            )}

            {/* Darkstore Status Indicator */}
            {shopData && (
              <div className="flex items-center gap-2 text-xs text-slate-300 bg-emerald-950/40 border border-emerald-500/20 px-3 py-2 rounded-xl">
                <Store size={15} className="text-emerald-400 shrink-0" />
                <span>Serving Darkstore: <strong className="text-white">{shopData.warehouse_name}</strong></span>
                <span className="text-slate-400">({shopData.distance_km.toFixed(1)} km away)</span>
              </div>
            )}
          </div>

          {/* Error / 404 No Darkstore in Range State */}
          {isError && (
            <div className="p-6 sm:p-8 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center mx-auto">
                <AlertTriangle size={24} />
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-serif text-white">No Darkstore Available in Range</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                  {(error as any)?.response?.data?.error?.message ||
                    (error as any)?.response?.data?.detail ||
                    'There are no active fulfillment centers within the 10km delivery radius of your location.'}
                </p>
              </div>
              <button
                onClick={() => {
                  setLat(DEFAULT_LAT);
                  setLon(DEFAULT_LON);
                  localStorage.setItem('user_lat', DEFAULT_LAT.toString());
                  localStorage.setItem('user_lon', DEFAULT_LON.toString());
                }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 transition-colors inline-flex items-center gap-2 cursor-pointer"
              >
                <RefreshCw size={14} />
                <span>Reset Location to Katpadi, Vellore (12.97, 79.14)</span>
              </button>
            </div>
          )}

          {/* Loading Grid Skeleton */}
          {isLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-44 rounded-2xl bg-[#121824] border border-slate-800 p-4 animate-pulse space-y-3">
                  <div className="h-4 bg-slate-800 rounded w-3/4" />
                  <div className="h-3 bg-slate-800/60 rounded w-1/2" />
                  <div className="h-8 bg-slate-800 rounded w-full mt-6" />
                </div>
              ))}
            </div>
          )}

          {/* Product Grid */}
          {shopData && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                  Available Catalog ({shopData.products.length} Items)
                </h2>
                <button
                  onClick={() => refetch()}
                  className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                >
                  <RefreshCw size={13} />
                  <span>Refresh Stock</span>
                </button>
              </div>

              {shopData.products.length === 0 ? (
                <div className="p-8 rounded-2xl bg-[#121824] border border-slate-800 text-center text-slate-400 text-xs">
                  No products currently in stock at this darkstore location.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {shopData.products.map((prod) => {
                    const inCart = cart[prod.id];
                    const cartQty = inCart ? inCart.cartQuantity : 0;
                    const isOutOfStock = prod.available_quantity === 0;

                    return (
                      <div
                        key={prod.id}
                        className={`p-4 rounded-2xl border flex flex-col justify-between transition-all ${
                          isOutOfStock
                            ? 'bg-[#0E131D] border-slate-800/60 opacity-60'
                            : 'bg-[#121824] border-slate-800 hover:border-slate-700 shadow-md'
                        }`}
                      >
                        <div className="space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="font-medium text-sm text-white line-clamp-2">{prod.name}</h3>
                            <span className="text-xs font-mono font-semibold text-emerald-400 shrink-0">
                              ₹{prod.price.toFixed(2)}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60">
                              {prod.category || 'General'}
                            </span>
                            <span>{prod.unit_weight_kg} kg</span>
                          </div>
                        </div>

                        <div className="pt-4 mt-2 border-t border-slate-800/80 flex items-center justify-between">
                          {isOutOfStock ? (
                            <span className="text-xs font-semibold text-red-400 bg-red-500/10 px-2.5 py-1 rounded-lg border border-red-500/20">
                              Out of Stock
                            </span>
                          ) : (
                            <span className="text-[11px] text-slate-400">
                              Stock: <strong className="text-slate-200">{prod.available_quantity}</strong>
                            </span>
                          )}

                          {!isOutOfStock && (
                            <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-700 rounded-xl p-1">
                              {cartQty > 0 ? (
                                <>
                                  <button
                                    onClick={() => updateCartQty(prod, -1)}
                                    className="w-6 h-6 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center transition-colors cursor-pointer"
                                  >
                                    <Minus size={13} />
                                  </button>
                                  <span className="w-6 text-center text-xs font-semibold text-white">
                                    {cartQty}
                                  </span>
                                  <button
                                    onClick={() => updateCartQty(prod, 1)}
                                    disabled={cartQty >= prod.available_quantity}
                                    className="w-6 h-6 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white flex items-center justify-center transition-colors cursor-pointer"
                                  >
                                    <Plus size={13} />
                                  </button>
                                </>
                              ) : (
                                <button
                                  onClick={() => updateCartQty(prod, 1)}
                                  className="px-3 py-1 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-semibold rounded-lg flex items-center gap-1 shadow-sm transition-all cursor-pointer"
                                >
                                  <Plus size={13} />
                                  <span>Add</span>
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Shopping Cart & Checkout Drawer */}
        <div className="lg:col-span-4">
          <div className="sticky top-20 card p-5 bg-[#121824] border border-slate-800 rounded-2xl shadow-xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <ShoppingBag size={18} className="text-emerald-400" />
                <h2 className="font-serif text-base font-semibold text-white">Your Cart</h2>
              </div>
              <span className="text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2.5 py-0.5 rounded-full">
                {totalItemsCount} {totalItemsCount === 1 ? 'Item' : 'Items'}
              </span>
            </div>

            {checkoutError && (
              <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-xs flex items-start gap-2">
                <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                <span>{checkoutError}</span>
              </div>
            )}

            {cartList.length === 0 ? (
              <div className="py-10 text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-slate-900 text-slate-600 flex items-center justify-center mx-auto">
                  <Package size={24} />
                </div>
                <p className="text-xs text-slate-400">Your cart is empty. Add products from the catalog to build your order.</p>
              </div>
            ) : (
              <>
                {/* Cart Item List */}
                <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
                  {cartList.map((item) => (
                    <div key={item.id} className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800/80 flex items-center justify-between gap-2 text-xs">
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-slate-200 truncate">{item.name}</p>
                        <p className="text-[11px] text-slate-400">₹{item.price.toFixed(2)} × {item.cartQuantity}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-mono font-semibold text-emerald-400">
                          ₹{(item.price * item.cartQuantity).toFixed(2)}
                        </span>
                        <button
                          onClick={() => removeFromCart(item.id)}
                          className="p-1 text-slate-500 hover:text-red-400 transition-colors"
                          title="Remove item"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Delivery Address Field */}
                <div className="space-y-1.5 pt-2 border-t border-slate-800">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <MapPin size={14} className="text-slate-400" />
                    <span>Delivery Address</span>
                  </label>
                  <textarea
                    rows={2}
                    required
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Enter full street address for instant delivery..."
                    className="w-full bg-slate-900 border border-slate-700/80 focus:border-indigo-500 rounded-xl p-2.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                {/* Totals Summary */}
                <div className="space-y-2 pt-2 border-t border-slate-800 text-xs">
                  <div className="flex justify-between text-slate-400">
                    <span>Est. Payload Weight:</span>
                    <span>{totalWeight.toFixed(2)} kg</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Delivery Fee (Hyperlocal):</span>
                    <span className="text-emerald-400">FREE</span>
                  </div>
                  <div className="flex justify-between text-sm font-semibold text-white pt-2 border-t border-slate-800">
                    <span>Grand Total:</span>
                    <span className="font-mono text-emerald-400">₹{totalPrice.toFixed(2)}</span>
                  </div>
                </div>

                {/* Place Order Button */}
                <button
                  type="button"
                  onClick={handleCheckout}
                  disabled={checkoutMutation.isPending}
                  className="w-full py-3 px-4 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold text-xs rounded-xl shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                >
                  {checkoutMutation.isPending ? (
                    <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>Place Order</span>
                      <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
