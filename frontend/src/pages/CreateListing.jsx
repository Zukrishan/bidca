import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, API, formatApiErrorDetail, formatCAD } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import { toast } from "sonner";
import {
  Camera,
  X,
  Gavel,
  Tag,
  Lightning,
  Clock,
  Package,
  Info,
  ArrowRight,
  CheckCircle
} from "@phosphor-icons/react";

export default function CreateListing() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [categories, setCategories] = useState({});
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [images, setImages] = useState([]);
  const [step, setStep] = useState(1);

  const [formData, setFormData] = useState({
    title: "",
    category: "",
    subcategory: "",
    description: "",
    condition: "good",
    city: user?.city || "",
    province: "British Columbia",
    listing_type: "auction",
    starting_bid: "",
    reserve_price: "",
    buy_it_now_price: "",
    duration_days: 7,
    shipping_cost: "0",
    shipping_from: "British Columbia",
    accepts_best_offer: false
  });

  useEffect(() => {
    fetchCategories();
    fetchCities();
  }, []);

  const fetchCategories = async () => {
    try {
      const { data } = await axios.get(`${API}/categories`);
      setCategories(data.categories || {});
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const fetchCities = async () => {
    try {
      const { data } = await axios.get(`${API}/cities`);
      setCities(data.cities || []);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    if (images.length + files.length > 10) {
      toast.error("Maximum 10 images allowed");
      return;
    }
    const newImages = files.map((file) => URL.createObjectURL(file));
    setImages([...images, ...newImages]);
    toast.info("Images added (MOCK - requires Cloudinary credentials)");
  };

  const removeImage = (index) => {
    setImages(images.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.title || !formData.category || !formData.description || !formData.city) {
      toast.error("Please fill in all required fields");
      return;
    }

    if (formData.listing_type !== "fixed_price" && !formData.starting_bid) {
      toast.error("Please enter a starting bid");
      return;
    }

    if (formData.listing_type === "fixed_price" && !formData.buy_it_now_price) {
      toast.error("Please enter a price");
      return;
    }

    setLoading(true);

    try {
      const payload = {
        title: formData.title,
        category: formData.category,
        subcategory: formData.subcategory || null,
        description: formData.description,
        condition: formData.condition,
        city: formData.city,
        province: formData.province,
        listing_type: formData.listing_type,
        images: images,
        starting_bid: parseFloat(formData.starting_bid) || 0,
        reserve_price: formData.reserve_price ? parseFloat(formData.reserve_price) : null,
        buy_it_now_price: formData.buy_it_now_price ? parseFloat(formData.buy_it_now_price) : null,
        duration_days: formData.duration_days,
        shipping_cost: parseFloat(formData.shipping_cost) || 0,
        shipping_from: formData.shipping_from,
        accepts_best_offer: formData.accepts_best_offer
      };

      await axios.post(`${API}/listings`, payload);
      toast.success("Listing created! Awaiting admin approval.");
      navigate("/seller");
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  const conditions = [
    { value: "new", label: "New", desc: "Brand new, unused" },
    { value: "like_new", label: "Like New", desc: "Barely used, no defects" },
    { value: "good", label: "Good", desc: "Normal wear, fully functional" },
    { value: "fair", label: "Fair", desc: "Some wear, works well" },
    { value: "poor", label: "Poor", desc: "Heavy wear, still works" }
  ];

  const durations = [1, 3, 5, 7, 10];

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="font-heading text-3xl font-bold">Create Listing</h1>
            <p className="text-muted-foreground mt-1">List your item for auction or fixed price</p>
          </div>

          {/* Progress */}
          <div className="flex items-center gap-2 mb-6">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`flex-1 h-2 ${step >= s ? 'bg-primary' : 'bg-border'}`}
              />
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            {/* Step 1: Listing Type & Photos */}
            {step === 1 && (
              <div className="space-y-6">
                {/* Listing Type */}
                <div className="bg-white border border-border p-6">
                  <h2 className="font-bold text-lg mb-4">Listing Type</h2>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, listing_type: "auction" })}
                      className={`p-4 border-2 text-center transition-colors ${
                        formData.listing_type === "auction" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                      }`}
                    >
                      <Gavel className="h-8 w-8 text-primary mx-auto mb-2" />
                      <p className="font-bold">Auction</p>
                      <p className="text-xs text-muted-foreground">Timed bidding</p>
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, listing_type: "auction_bin" })}
                      className={`p-4 border-2 text-center transition-colors ${
                        formData.listing_type === "auction_bin" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                      }`}
                    >
                      <Lightning className="h-8 w-8 text-primary mx-auto mb-2" />
                      <p className="font-bold">Auction + BIN</p>
                      <p className="text-xs text-muted-foreground">Bid or Buy Now</p>
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, listing_type: "fixed_price" })}
                      className={`p-4 border-2 text-center transition-colors ${
                        formData.listing_type === "fixed_price" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                      }`}
                    >
                      <Tag className="h-8 w-8 text-primary mx-auto mb-2" />
                      <p className="font-bold">Fixed Price</p>
                      <p className="text-xs text-muted-foreground">Buy Now only</p>
                    </button>
                  </div>
                </div>

                {/* Photos */}
                <div className="bg-white border border-border p-6">
                  <h2 className="font-bold text-lg mb-2">Photos</h2>
                  <p className="text-sm text-muted-foreground mb-4">
                    Add up to 10 photos. First image will be the cover.
                  </p>

                  <div className="grid grid-cols-5 gap-3">
                    {images.map((img, i) => (
                      <div key={i} className="relative aspect-square bg-muted">
                        <img src={img} alt="" className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={() => removeImage(i)}
                          className="absolute -top-2 -right-2 w-6 h-6 bg-destructive text-white flex items-center justify-center rounded-full"
                        >
                          <X className="h-4 w-4" />
                        </button>
                        {i === 0 && (
                          <span className="absolute bottom-0 left-0 right-0 bg-primary text-white text-xs text-center py-0.5">
                            Cover
                          </span>
                        )}
                      </div>
                    ))}
                    
                    {images.length < 10 && (
                      <label className="aspect-square border-2 border-dashed border-border flex flex-col items-center justify-center cursor-pointer hover:border-primary transition-colors">
                        <input
                          type="file"
                          accept="image/*"
                          multiple
                          onChange={handleImageUpload}
                          className="hidden"
                        />
                        <Camera className="h-6 w-6 text-muted-foreground mb-1" />
                        <span className="text-xs text-muted-foreground">Add</span>
                      </label>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="w-full py-3 bg-primary text-white font-bold"
                >
                  Continue
                </button>
              </div>
            )}

            {/* Step 2: Details */}
            {step === 2 && (
              <div className="space-y-6">
                <div className="bg-white border border-border p-6">
                  <h2 className="font-bold text-lg mb-4">Item Details</h2>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Title *</label>
                      <input
                        type="text"
                        value={formData.title}
                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                        className="w-full px-4 py-2 border border-input focus:border-primary outline-none"
                        placeholder="What are you selling?"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">Category *</label>
                        <select
                          value={formData.category}
                          onChange={(e) => setFormData({ ...formData, category: e.target.value, subcategory: "" })}
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none"
                          required
                        >
                          <option value="">Select category</option>
                          {Object.keys(categories).map((cat) => (
                            <option key={cat} value={cat}>{cat}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">Subcategory</label>
                        <select
                          value={formData.subcategory}
                          onChange={(e) => setFormData({ ...formData, subcategory: e.target.value })}
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none"
                          disabled={!formData.category}
                        >
                          <option value="">Select subcategory</option>
                          {formData.category && categories[formData.category]?.map((sub) => (
                            <option key={sub} value={sub}>{sub}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Description *</label>
                      <textarea
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        rows={5}
                        className="w-full px-4 py-2 border border-input focus:border-primary outline-none resize-none"
                        placeholder="Describe your item in detail..."
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">Condition *</label>
                      <div className="grid grid-cols-5 gap-2">
                        {conditions.map((c) => (
                          <button
                            key={c.value}
                            type="button"
                            onClick={() => setFormData({ ...formData, condition: c.value })}
                            className={`p-2 border-2 text-center transition-colors ${
                              formData.condition === c.value ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                            }`}
                          >
                            <p className="font-medium text-sm">{c.label}</p>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">City *</label>
                        <select
                          value={formData.city}
                          onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none"
                          required
                        >
                          <option value="">Select city</option>
                          {cities.map((city) => (
                            <option key={city} value={city}>{city}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">Shipping Cost (CAD)</label>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={formData.shipping_cost}
                          onChange={(e) => setFormData({ ...formData, shipping_cost: e.target.value })}
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none"
                          placeholder="0 for free shipping"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="flex-1 py-3 border border-border font-medium"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    className="flex-1 py-3 bg-primary text-white font-bold"
                  >
                    Continue
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Pricing */}
            {step === 3 && (
              <div className="space-y-6">
                <div className="bg-white border border-border p-6">
                  <h2 className="font-bold text-lg mb-4">Pricing & Duration</h2>

                  <div className="space-y-4">
                    {formData.listing_type !== "fixed_price" && (
                      <>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium mb-1">Starting Bid (CAD) *</label>
                            <div className="relative">
                              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                              <input
                                type="number"
                                min="0.01"
                                step="0.01"
                                value={formData.starting_bid}
                                onChange={(e) => setFormData({ ...formData, starting_bid: e.target.value })}
                                className="w-full pl-8 pr-4 py-2 border border-input focus:border-primary outline-none"
                                placeholder="0.00"
                                required
                              />
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm font-medium mb-1">Reserve Price (Optional)</label>
                            <div className="relative">
                              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                              <input
                                type="number"
                                min="0"
                                step="0.01"
                                value={formData.reserve_price}
                                onChange={(e) => setFormData({ ...formData, reserve_price: e.target.value })}
                                className="w-full pl-8 pr-4 py-2 border border-input focus:border-primary outline-none"
                                placeholder="Minimum you'll accept"
                              />
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">Item won't sell below this</p>
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-medium mb-2">Auction Duration</label>
                          <div className="flex gap-2">
                            {durations.map((d) => (
                              <button
                                key={d}
                                type="button"
                                onClick={() => setFormData({ ...formData, duration_days: d })}
                                className={`flex-1 py-2 border-2 text-center ${
                                  formData.duration_days === d ? "border-primary bg-primary/5" : "border-border"
                                }`}
                              >
                                {d} day{d > 1 ? 's' : ''}
                              </button>
                            ))}
                          </div>
                        </div>
                      </>
                    )}

                    {(formData.listing_type === "fixed_price" || formData.listing_type === "auction_bin") && (
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          {formData.listing_type === "fixed_price" ? "Price" : "Buy It Now Price"} (CAD) *
                        </label>
                        <div className="relative max-w-xs">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                          <input
                            type="number"
                            min="0.01"
                            step="0.01"
                            value={formData.buy_it_now_price}
                            onChange={(e) => setFormData({ ...formData, buy_it_now_price: e.target.value })}
                            className="w-full pl-8 pr-4 py-2 border border-input focus:border-primary outline-none"
                            placeholder="0.00"
                            required={formData.listing_type === "fixed_price"}
                          />
                        </div>
                        {formData.listing_type === "auction_bin" && (
                          <p className="text-xs text-muted-foreground mt-1">
                            Must be higher than starting bid. Ends auction immediately when purchased.
                          </p>
                        )}
                      </div>
                    )}

                    {formData.listing_type === "fixed_price" && (
                      <div>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.accepts_best_offer}
                            onChange={(e) => setFormData({ ...formData, accepts_best_offer: e.target.checked })}
                            className="accent-primary w-4 h-4"
                          />
                          <span className="text-sm font-medium">Accept Best Offers</span>
                        </label>
                        <p className="text-xs text-muted-foreground ml-6">Allow buyers to submit offers below your price</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Fee Notice */}
                <div className="bg-yellow-50 border border-yellow-200 p-4 flex items-start gap-3">
                  <Info className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-yellow-800">Seller Fees</p>
                    <p className="text-yellow-700">
                      10% fee on final sale price. No listing fees. You only pay when your item sells.
                    </p>
                  </div>
                </div>

                {/* Review Notice */}
                <div className="bg-primary/10 border border-primary/20 p-4 flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium">Admin Review Required</p>
                    <p className="text-muted-foreground">
                      Your listing will be reviewed before going live. Usually takes less than 24 hours.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="flex-1 py-3 border border-border font-medium"
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 py-3 bg-primary text-white font-bold disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        Create Listing
                        <ArrowRight className="h-5 w-5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>

      <Footer />
    </div>
  );
}
