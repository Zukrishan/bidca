import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, API, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import { toast } from "sonner";
import {
  Camera,
  X,
  Plus,
  Gavel,
  Tag,
  MapPin,
  Clock,
  Info,
  ArrowRight
} from "@phosphor-icons/react";

export default function CreateListing() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [categories, setCategories] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [images, setImages] = useState([]);
  const [uploadingImages, setUploadingImages] = useState(false);

  const [formData, setFormData] = useState({
    title: "",
    category: "",
    description: "",
    city: user?.city || "",
    listing_type: "auction",
    starting_bid: "",
    bid_increment: "5",
    duration_hours: "24",
    fixed_price: ""
  });

  useEffect(() => {
    fetchCategories();
    fetchCities();
  }, []);

  const fetchCategories = async () => {
    try {
      const { data } = await axios.get(`${API}/categories`);
      setCategories(data.categories || []);
    } catch (error) {
      console.error("Error fetching categories:", error);
    }
  };

  const fetchCities = async () => {
    try {
      const { data } = await axios.get(`${API}/cities`);
      setCities(data.cities || []);
    } catch (error) {
      console.error("Error fetching cities:", error);
    }
  };

  // Mock image upload for now (Cloudinary requires real credentials)
  const handleImageUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (images.length + files.length > 10) {
      toast.error("Maximum 10 images allowed");
      return;
    }

    setUploadingImages(true);

    // For now, create object URLs as placeholders
    // In production, this would upload to Cloudinary
    const newImages = files.map((file) => URL.createObjectURL(file));
    setImages([...images, ...newImages]);
    
    toast.info("Images added (MOCK - Cloudinary integration requires real credentials)");
    setUploadingImages(false);
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

    if (formData.listing_type === "auction" && !formData.starting_bid) {
      toast.error("Please enter a starting bid");
      return;
    }

    if (formData.listing_type === "marketplace" && !formData.fixed_price) {
      toast.error("Please enter a price");
      return;
    }

    setLoading(true);

    try {
      const payload = {
        title: formData.title,
        category: formData.category,
        description: formData.description,
        city: formData.city,
        listing_type: formData.listing_type,
        images: images,
        starting_bid: parseFloat(formData.starting_bid) || 0,
        bid_increment: parseFloat(formData.bid_increment) || 5,
        duration_hours: parseInt(formData.duration_hours),
        fixed_price: formData.listing_type === "marketplace" ? parseFloat(formData.fixed_price) : null
      };

      await axios.post(`${API}/listings`, payload);
      toast.success("Listing created! It will be reviewed by admin before going live.");
      navigate("/seller");
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h1 className="font-heading text-3xl font-bold" data-testid="create-listing-title">
              Create Listing
            </h1>
            <p className="text-muted-foreground mt-2">
              List your item for auction or direct sale
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Listing Type */}
            <div className="bg-white border border-border p-6 mb-6">
              <h2 className="font-heading font-bold mb-4">Listing Type</h2>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, listing_type: "auction" })}
                  className={`p-4 border-2 transition-colors ${
                    formData.listing_type === "auction"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                  data-testid="type-auction"
                >
                  <Gavel className="h-8 w-8 text-primary mx-auto mb-2" />
                  <p className="font-medium">Auction</p>
                  <p className="text-sm text-muted-foreground">Timed bidding</p>
                </button>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, listing_type: "marketplace" })}
                  className={`p-4 border-2 transition-colors ${
                    formData.listing_type === "marketplace"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                  data-testid="type-marketplace"
                >
                  <Tag className="h-8 w-8 text-primary mx-auto mb-2" />
                  <p className="font-medium">Marketplace</p>
                  <p className="text-sm text-muted-foreground">Fixed price</p>
                </button>
              </div>
            </div>

            {/* Images */}
            <div className="bg-white border border-border p-6 mb-6">
              <h2 className="font-heading font-bold mb-4">Photos</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Add up to 10 photos. The first image will be the cover.
              </p>

              <div className="grid grid-cols-4 sm:grid-cols-5 gap-4">
                {images.map((img, i) => (
                  <div key={i} className="relative aspect-square bg-muted">
                    <img src={img} alt="" className="w-full h-full object-cover" />
                    <button
                      type="button"
                      onClick={() => removeImage(i)}
                      className="absolute -top-2 -right-2 w-6 h-6 bg-destructive text-white flex items-center justify-center"
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
                      disabled={uploadingImages}
                    />
                    {uploadingImages ? (
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        <Camera className="h-6 w-6 text-muted-foreground mb-1" />
                        <span className="text-xs text-muted-foreground">Add Photo</span>
                      </>
                    )}
                  </label>
                )}
              </div>
            </div>

            {/* Details */}
            <div className="bg-white border border-border p-6 mb-6">
              <h2 className="font-heading font-bold mb-4">Details</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2" htmlFor="title">
                    Title *
                  </label>
                  <input
                    id="title"
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    className="w-full px-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                    placeholder="What are you selling?"
                    required
                    data-testid="input-title"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2" htmlFor="category">
                      Category *
                    </label>
                    <select
                      id="category"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                      className="w-full px-4 py-3 border border-input bg-background focus:border-primary outline-none"
                      required
                      data-testid="input-category"
                    >
                      <option value="">Select category</option>
                      {categories.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2" htmlFor="city">
                      City *
                    </label>
                    <select
                      id="city"
                      value={formData.city}
                      onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                      className="w-full px-4 py-3 border border-input bg-background focus:border-primary outline-none"
                      required
                      data-testid="input-city"
                    >
                      <option value="">Select city</option>
                      {cities.map((city) => (
                        <option key={city} value={city}>{city}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2" htmlFor="description">
                    Description *
                  </label>
                  <textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={5}
                    className="w-full px-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none"
                    placeholder="Describe your item in detail..."
                    required
                    data-testid="input-description"
                  />
                </div>
              </div>
            </div>

            {/* Pricing */}
            <div className="bg-white border border-border p-6 mb-6">
              <h2 className="font-heading font-bold mb-4">Pricing</h2>

              {formData.listing_type === "auction" ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2" htmlFor="starting_bid">
                        Starting Bid *
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                        <input
                          id="starting_bid"
                          type="number"
                          min="1"
                          step="0.01"
                          value={formData.starting_bid}
                          onChange={(e) => setFormData({ ...formData, starting_bid: e.target.value })}
                          className="w-full pl-8 pr-4 py-3 border border-input bg-background focus:border-primary outline-none"
                          placeholder="0.00"
                          required
                          data-testid="input-starting-bid"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2" htmlFor="bid_increment">
                        Bid Increment
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                        <input
                          id="bid_increment"
                          type="number"
                          min="1"
                          step="1"
                          value={formData.bid_increment}
                          onChange={(e) => setFormData({ ...formData, bid_increment: e.target.value })}
                          className="w-full pl-8 pr-4 py-3 border border-input bg-background focus:border-primary outline-none"
                          data-testid="input-bid-increment"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Auction Duration
                    </label>
                    <div className="grid grid-cols-3 gap-4">
                      {["24", "48", "72"].map((hours) => (
                        <button
                          key={hours}
                          type="button"
                          onClick={() => setFormData({ ...formData, duration_hours: hours })}
                          className={`p-3 border-2 transition-colors flex items-center justify-center gap-2 ${
                            formData.duration_hours === hours
                              ? "border-primary bg-primary/5"
                              : "border-border hover:border-primary/50"
                          }`}
                          data-testid={`duration-${hours}`}
                        >
                          <Clock className="h-5 w-5" />
                          {hours} Hours
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium mb-2" htmlFor="fixed_price">
                    Price *
                  </label>
                  <div className="relative max-w-xs">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                    <input
                      id="fixed_price"
                      type="number"
                      min="1"
                      step="0.01"
                      value={formData.fixed_price}
                      onChange={(e) => setFormData({ ...formData, fixed_price: e.target.value })}
                      className="w-full pl-8 pr-4 py-3 border border-input bg-background focus:border-primary outline-none"
                      placeholder="0.00"
                      required
                      data-testid="input-fixed-price"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Info Notice */}
            <div className="bg-primary/10 border border-primary/20 p-4 mb-6 flex items-start gap-3">
              <Info className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium">Admin Review Required</p>
                <p className="text-muted-foreground">
                  Your listing will be reviewed by our team before going live. This usually takes less than 24 hours.
                </p>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-primary text-white font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              data-testid="submit-listing"
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
          </form>
        </div>
      </div>

      <Footer />
    </div>
  );
}
