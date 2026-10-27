import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth, API, formatApiErrorDetail } from "../App";
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
  LockSimple,
  Info,
  ArrowRight,
  CheckCircle,
  FloppyDisk,
  CaretLeft,
  CaretRight
} from "@phosphor-icons/react";

// Extra fields some categories ask for (FR-05) — mirrors backend constants.CATEGORY_FIELDS
const CATEGORY_FIELDS = {
  Vehicles: [
    { name: "year", label: "Year", type: "number" },
    { name: "make", label: "Make", type: "text" },
    { name: "model", label: "Model", type: "text" },
    { name: "mileage", label: "Mileage (km)", type: "number" }
  ],
  Electronics: [
    { name: "brand", label: "Brand", type: "text" },
    { name: "model", label: "Model", type: "text" }
  ]
};

const EMPTY_DISCLOSURE = {
  accident_history: null,
  accident_description: "",
  mechanical_issues: null,
  mechanical_description: "",
  previous_owners: "",
  safety_certificate: null,
  safety_certificate_url: "",
  odometer_km: "",
  liens: null
};

const LISTING_TYPES = [
  { value: "auction", label: "Auction", desc: "Timed bidding", Icon: Gavel },
  { value: "auction_bin", label: "Auction + BIN", desc: "Bid or Buy Now", Icon: Lightning },
  { value: "fixed_price", label: "Fixed Price", desc: "Buy Now only", Icon: Tag },
  { value: "private", label: "Private", desc: "Invite-only auction", Icon: LockSimple }
];

const isBlank = (v) => v === null || v === undefined || String(v).trim() === "";

// The vehicle disclosure (Q008) is complete when every yes/no is answered and each "yes" is explained
function disclosureComplete(d) {
  if ([d.accident_history, d.mechanical_issues, d.safety_certificate, d.liens].some((v) => v === null)) return false;
  if (isBlank(d.previous_owners) || isBlank(d.odometer_km)) return false;
  if (d.accident_history && isBlank(d.accident_description)) return false;
  if (d.mechanical_issues && isBlank(d.mechanical_description)) return false;
  return true;
}

function YesNo({ label, value, onChange, testId }) {
  return (
    <div>
      <p className="block text-sm font-medium mb-1">{label} *</p>
      <div className="flex gap-2" role="radiogroup" aria-label={label}>
        {[true, false].map((v) => (
          <button
            key={String(v)}
            type="button"
            role="radio"
            aria-checked={value === v}
            onClick={() => onChange(v)}
            data-testid={`${testId}-${v ? "yes" : "no"}`}
            className={`px-4 py-1.5 border-2 text-sm ${value === v ? "border-primary bg-primary/5" : "border-border"}`}
          >
            {v ? "Yes" : "No"}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function CreateListing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const draftId = searchParams.get("draft");

  const [categories, setCategories] = useState({});
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [images, setImages] = useState([]);
  const [step, setStep] = useState(1);
  const [dragIndex, setDragIndex] = useState(null);
  const [quota, setQuota] = useState(null);
  const [invitees, setInvitees] = useState("");

  const [formData, setFormData] = useState({
    title: "",
    category: "",
    subcategory: "",
    description: "",
    condition: "",
    city: user?.city || "",
    province: "British Columbia",
    listing_type: "auction",
    starting_bid: "",
    reserve_price: "",
    buy_it_now_price: "",
    duration_days: 7,
    accepts_best_offer: false
  });
  const [categoryFields, setCategoryFields] = useState({});
  const [disclosure, setDisclosure] = useState(EMPTY_DISCLOSURE);

  useEffect(() => {
    fetchCategories();
    fetchCities();
    axios.get(`${API}/users/me/listing-quota`).then(({ data }) => setQuota(data)).catch(() => {});
  }, []);

  // Editing a saved draft (FR-05)
  useEffect(() => {
    if (!draftId) return;
    axios
      .get(`${API}/listings/${draftId}`)
      .then(({ data }) => {
        if (data.status !== "draft") {
          toast.error("Only drafts can be edited");
          navigate("/seller");
          return;
        }
        setFormData((f) => ({
          ...f,
          ...Object.fromEntries(Object.keys(f).map((k) => [k, data[k] ?? f[k]])),
          subcategory: data.subcategory || "",
          starting_bid: data.listing_type === "fixed_price" ? "" : data.starting_bid ?? ""
        }));
        setImages(data.images || []);
        setCategoryFields(data.category_fields || {});
        setDisclosure({ ...EMPTY_DISCLOSURE, ...(data.vehicle_disclosure || {}) });
      })
      .catch(() => {
        toast.error("Draft not found");
        navigate("/seller");
      });
  }, [draftId, navigate]);

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

  // Drag-and-drop reordering (FR-05), plus arrow buttons for keyboard and touch users
  const moveImage = (from, to) => {
    if (from === to || to < 0 || to >= images.length) return;
    const next = [...images];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    setImages(next);
  };

  const isVehicle = formData.category === "Vehicles";
  const extraFields = CATEGORY_FIELDS[formData.category] || [];
  const detailsComplete =
    !isBlank(formData.title) &&
    !isBlank(formData.category) &&
    !isBlank(formData.description) &&
    !isBlank(formData.condition) &&
    !isBlank(formData.city) &&
    (!isVehicle || disclosureComplete(disclosure));
  const priceComplete =
    formData.listing_type === "fixed_price" ? !isBlank(formData.buy_it_now_price) : !isBlank(formData.starting_bid);

  const buildPayload = (draft) => {
    const numberOrNull = (v) => (isBlank(v) ? null : parseFloat(v));
    const intOrNull = (v) => (isBlank(v) ? null : parseInt(v, 10));
    const payload = {
      title: formData.title,
      category: formData.category || null,
      subcategory: formData.subcategory || null,
      description: formData.description,
      condition: formData.condition || "good",
      city: formData.city || null,
      province: formData.province,
      listing_type: formData.listing_type,
      images: images,
      starting_bid: formData.listing_type === "fixed_price" ? 0 : numberOrNull(formData.starting_bid),
      reserve_price: numberOrNull(formData.reserve_price),
      buy_it_now_price: numberOrNull(formData.buy_it_now_price),
      duration_days: formData.duration_days,
      accepts_best_offer: formData.accepts_best_offer,
      category_fields: extraFields.length ? categoryFields : null,
      vehicle_disclosure: isVehicle
        ? {
            ...disclosure,
            previous_owners: intOrNull(disclosure.previous_owners),
            odometer_km: intOrNull(disclosure.odometer_km),
            safety_certificate_url: disclosure.safety_certificate_url || null
          }
        : null,
      draft
    };
    if (formData.listing_type === "private") {
      payload.invitees = invitees
        .split(/[\n,;]+/)
        .map((s) => s.trim())
        .filter(Boolean);
    }
    return payload;
  };

  const save = async (draft) => {
    if (!draft && !(detailsComplete && priceComplete)) {
      toast.error("Please fill in all required fields");
      return;
    }
    if (draft && isBlank(formData.title)) {
      toast.error("Give your draft a title first");
      return;
    }
    setLoading(true);
    try {
      const payload = buildPayload(draft);
      if (draftId) {
        if (formData.listing_type !== "private") delete payload.invitees;
        else if (!payload.invitees.length) delete payload.invitees; // keep the invites already on the draft
        await axios.put(`${API}/listings/${draftId}`, payload);
        if (!draft) await axios.post(`${API}/listings/${draftId}/submit`);
      } else {
        await axios.post(`${API}/listings`, payload);
      }
      toast.success(draft ? "Draft saved. Only you can see it." : "Listing submitted! Awaiting admin approval.");
      navigate("/seller");
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    save(false);
  };

  const conditions = [
    { value: "new", label: "New", desc: "Brand new, unused" },
    { value: "like_new", label: "Like New", desc: "Barely used, no defects" },
    { value: "good", label: "Good", desc: "Normal wear, fully functional" },
    { value: "fair", label: "Fair", desc: "Some wear, works well" },
    { value: "poor", label: "Poor", desc: "Heavy wear, still works" }
  ];

  const durations = [1, 3, 5, 7, 10];
  const capReached = quota && quota.remaining <= 0;

  const draftButton = (
    <button
      type="button"
      onClick={() => save(true)}
      disabled={loading}
      className="flex-1 py-3 border border-border font-medium flex items-center justify-center gap-2 disabled:opacity-50"
      data-testid="save-draft-btn"
    >
      <FloppyDisk className="h-5 w-5" />
      Save as draft
    </button>
  );

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h1 className="font-heading text-3xl font-bold">{draftId ? "Edit Draft" : "Create Listing"}</h1>
            <p className="text-muted-foreground mt-1">List your item for auction or fixed price. Fields marked * are required.</p>
            {quota && (
              <p className={`text-sm mt-2 ${capReached ? "text-destructive font-medium" : "text-muted-foreground"}`} data-testid="listing-quota">
                {quota.used} of {quota.cap} listings used this month (Pacific time).
                {capReached && " You can still save drafts and submit them next month."}
              </p>
            )}
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
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    {LISTING_TYPES.map(({ value, label, desc, Icon }) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setFormData({ ...formData, listing_type: value })}
                        className={`p-4 border-2 text-center transition-colors ${
                          formData.listing_type === value ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                        }`}
                        data-testid={`type-${value}`}
                      >
                        <Icon className="h-8 w-8 text-primary mx-auto mb-2" />
                        <p className="font-bold">{label}</p>
                        <p className="text-xs text-muted-foreground">{desc}</p>
                      </button>
                    ))}
                  </div>
                  {formData.listing_type === "private" && (
                    <p className="text-sm text-muted-foreground mt-4">
                      Only people you invite can see and bid on a private listing. It never appears in search or on the
                      home page, it still needs admin approval, and it has no ratings.
                    </p>
                  )}
                </div>

                {/* Photos */}
                <div className="bg-white border border-border p-6">
                  <h2 className="font-bold text-lg mb-2">Photos</h2>
                  <p className="text-sm text-muted-foreground mb-4">
                    Add up to 10 photos. Drag to reorder — the first image is the cover.
                  </p>

                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
                    {images.map((img, i) => (
                      <div
                        key={img}
                        draggable
                        onDragStart={(e) => {
                          setDragIndex(i);
                          e.dataTransfer.effectAllowed = "move";
                        }}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => {
                          e.preventDefault();
                          if (dragIndex !== null) moveImage(dragIndex, i);
                          setDragIndex(null);
                        }}
                        onDragEnd={() => setDragIndex(null)}
                        className={`relative aspect-square bg-muted cursor-move ${dragIndex === i ? "opacity-50" : ""}`}
                        data-testid={`image-${i}`}
                      >
                        <img src={img} alt={`Photo ${i + 1}`} className="w-full h-full object-cover pointer-events-none" />
                        <button
                          type="button"
                          onClick={() => removeImage(i)}
                          aria-label={`Remove photo ${i + 1}`}
                          className="absolute -top-2 -right-2 w-6 h-6 bg-destructive text-white flex items-center justify-center rounded-full"
                        >
                          <X className="h-4 w-4" />
                        </button>
                        <div className="absolute top-1 left-1 flex gap-1">
                          {i > 0 && (
                            <button type="button" onClick={() => moveImage(i, i - 1)} aria-label={`Move photo ${i + 1} earlier`}
                              className="w-6 h-6 bg-white/90 border border-border flex items-center justify-center">
                              <CaretLeft className="h-3 w-3" />
                            </button>
                          )}
                          {i < images.length - 1 && (
                            <button type="button" onClick={() => moveImage(i, i + 1)} aria-label={`Move photo ${i + 1} later`}
                              className="w-6 h-6 bg-white/90 border border-border flex items-center justify-center">
                              <CaretRight className="h-3 w-3" />
                            </button>
                          )}
                        </div>
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
                      <label htmlFor="title" className="block text-sm font-medium mb-1">Title *</label>
                      <input
                        id="title"
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
                        <label htmlFor="category" className="block text-sm font-medium mb-1">Category *</label>
                        <select
                          id="category"
                          value={formData.category}
                          onChange={(e) => {
                            setFormData({ ...formData, category: e.target.value, subcategory: "" });
                            setCategoryFields({});
                          }}
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
                        <label htmlFor="subcategory" className="block text-sm font-medium mb-1">Subcategory</label>
                        <select
                          id="subcategory"
                          value={formData.subcategory}
                          onChange={(e) => setFormData({ ...formData, subcategory: e.target.value })}
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none disabled:opacity-50"
                          disabled={!formData.category}
                        >
                          <option value="">{formData.category ? "Select subcategory" : "Choose a category first"}</option>
                          {formData.category && categories[formData.category]?.map((sub) => (
                            <option key={sub} value={sub}>{sub}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {extraFields.length > 0 && (
                      <div className="grid grid-cols-2 gap-4" data-testid="category-fields">
                        {extraFields.map((f) => (
                          <div key={f.name}>
                            <label htmlFor={`cf-${f.name}`} className="block text-sm font-medium mb-1">{f.label}</label>
                            <input
                              id={`cf-${f.name}`}
                              type={f.type}
                              min={f.type === "number" ? 0 : undefined}
                              value={categoryFields[f.name] ?? ""}
                              onChange={(e) => setCategoryFields({ ...categoryFields, [f.name]: e.target.value })}
                              className="w-full px-4 py-2 border border-input focus:border-primary outline-none"
                            />
                          </div>
                        ))}
                      </div>
                    )}

                    <div>
                      <label htmlFor="description" className="block text-sm font-medium mb-1">Description *</label>
                      <textarea
                        id="description"
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        rows={5}
                        className="w-full px-4 py-2 border border-input focus:border-primary outline-none resize-none"
                        placeholder="Describe your item in detail..."
                        required
                      />
                    </div>

                    <div>
                      <p className="block text-sm font-medium mb-2">Condition *</p>
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
                        <label htmlFor="city" className="block text-sm font-medium mb-1">City *</label>
                        <select
                          id="city"
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
                    </div>
                  </div>
                </div>

                {/* Vehicle disclosure (FR-30, Q008) — required for Vehicles, shown on the listing page */}
                {isVehicle && (
                  <div className="bg-white border border-border p-6" data-testid="vehicle-disclosure">
                    <h2 className="font-bold text-lg mb-1">Vehicle disclosure</h2>
                    <p className="text-sm text-muted-foreground mb-4">
                      Buyers see these answers on your listing. Answer honestly — they help buyers decide before viewing.
                    </p>
                    <div className="space-y-4">
                      <YesNo label="Any accident history?" value={disclosure.accident_history} testId="accident"
                        onChange={(v) => setDisclosure({ ...disclosure, accident_history: v })} />
                      {disclosure.accident_history && (
                        <textarea rows={2} aria-label="Describe the accident history"
                          value={disclosure.accident_description || ""}
                          onChange={(e) => setDisclosure({ ...disclosure, accident_description: e.target.value })}
                          placeholder="Briefly describe what happened and what was repaired *"
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none resize-none" />
                      )}
                      <YesNo label="Any known mechanical issues?" value={disclosure.mechanical_issues} testId="mechanical"
                        onChange={(v) => setDisclosure({ ...disclosure, mechanical_issues: v })} />
                      {disclosure.mechanical_issues && (
                        <textarea rows={2} aria-label="Describe the mechanical issues"
                          value={disclosure.mechanical_description || ""}
                          onChange={(e) => setDisclosure({ ...disclosure, mechanical_description: e.target.value })}
                          placeholder="Describe the known issues *"
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none resize-none" />
                      )}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label htmlFor="owners" className="block text-sm font-medium mb-1">Number of previous owners *</label>
                          <input id="owners" type="number" min="0" value={disclosure.previous_owners ?? ""}
                            onChange={(e) => setDisclosure({ ...disclosure, previous_owners: e.target.value })}
                            className="w-full px-4 py-2 border border-input focus:border-primary outline-none" />
                        </div>
                        <div>
                          <label htmlFor="odometer" className="block text-sm font-medium mb-1">Odometer reading (km) *</label>
                          <input id="odometer" type="number" min="0" value={disclosure.odometer_km ?? ""}
                            onChange={(e) => setDisclosure({ ...disclosure, odometer_km: e.target.value })}
                            className="w-full px-4 py-2 border border-input focus:border-primary outline-none" />
                        </div>
                      </div>
                      <YesNo label="Valid BC inspection or safety certificate?" value={disclosure.safety_certificate} testId="certificate"
                        onChange={(v) => setDisclosure({ ...disclosure, safety_certificate: v })} />
                      {disclosure.safety_certificate && (
                        <div>
                          <label htmlFor="cert-url" className="block text-sm font-medium mb-1">Certificate link (optional)</label>
                          <input id="cert-url" type="url" value={disclosure.safety_certificate_url || ""}
                            onChange={(e) => setDisclosure({ ...disclosure, safety_certificate_url: e.target.value })}
                            placeholder="https://"
                            className="w-full px-4 py-2 border border-input focus:border-primary outline-none" />
                        </div>
                      )}
                      <YesNo label="Any liens or loans outstanding on the vehicle?" value={disclosure.liens} testId="liens"
                        onChange={(v) => setDisclosure({ ...disclosure, liens: v })} />
                    </div>
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="flex-1 py-3 border border-border font-medium"
                  >
                    Back
                  </button>
                  {draftButton}
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    disabled={!detailsComplete}
                    title={detailsComplete ? undefined : "Fill in every field marked *"}
                    className="flex-1 py-3 bg-primary text-white font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="details-continue"
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

                    {formData.listing_type === "private" && (
                      <div>
                        <label htmlFor="invitees" className="block text-sm font-medium mb-1">Invite people</label>
                        <textarea
                          id="invitees"
                          rows={3}
                          value={invitees}
                          onChange={(e) => setInvitees(e.target.value)}
                          placeholder="BidCa emails or phone numbers, one per line"
                          className="w-full px-4 py-2 border border-input focus:border-primary outline-none resize-none"
                          data-testid="invitees-input"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          They need a BidCa account. You'll also get a private invite link to send by text or WhatsApp —
                          find it, and add or remove people, in your seller dashboard.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Fee Notice */}
                <div className="bg-yellow-50 border border-yellow-200 p-4 flex items-start gap-3">
                  <Info className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-yellow-800">No fees, no payments</p>
                    <p className="text-yellow-700">
                      Listing is free. BidCa never handles money — you and the buyer arrange the exchange directly.
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
                  {draftButton}
                  <button
                    type="submit"
                    disabled={loading || !detailsComplete || !priceComplete || capReached}
                    className="flex-1 py-3 bg-primary text-white font-bold disabled:opacity-50 flex items-center justify-center gap-2"
                    data-testid="submit-listing-btn"
                  >
                    {loading ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        Submit for review
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
