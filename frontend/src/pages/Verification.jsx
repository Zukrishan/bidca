import React, { useState, useEffect } from "react";
import { useAuth, API, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import { toast } from "sonner";
import {
  ShieldCheck,
  Camera,
  IdentificationCard,
  User,
  CheckCircle,
  Clock,
  Warning,
  Info,
  Upload
} from "@phosphor-icons/react";

export default function Verification() {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [verificationStatus, setVerificationStatus] = useState(null);
  const [governmentId, setGovernmentId] = useState(null);
  const [selfie, setSelfie] = useState(null);
  const [governmentIdPreview, setGovernmentIdPreview] = useState(null);
  const [selfiePreview, setSelfiePreview] = useState(null);

  useEffect(() => {
    fetchVerificationStatus();
  }, []);

  const fetchVerificationStatus = async () => {
    try {
      const { data } = await axios.get(`${API}/verification/status`);
      setVerificationStatus(data);
    } catch (error) {
      console.error("Error fetching verification status:", error);
    }
  };

  const handleFileChange = (type, e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Create preview
    const previewUrl = URL.createObjectURL(file);
    
    if (type === "id") {
      setGovernmentId(file);
      setGovernmentIdPreview(previewUrl);
    } else {
      setSelfie(file);
      setSelfiePreview(previewUrl);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!governmentIdPreview || !selfiePreview) {
      toast.error("Please upload both government ID and selfie");
      return;
    }

    setLoading(true);

    try {
      // For mock, we use the preview URLs
      // In production, these would be uploaded to Cloudinary first
      await axios.post(`${API}/verification/submit`, {
        government_id_url: governmentIdPreview,
        selfie_url: selfiePreview
      });

      toast.success("Verification submitted! Admin will review your documents.");
      await refreshUser();
      await fetchVerificationStatus();
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  const renderStatusContent = () => {
    if (user?.verification_badge || user?.verification_status === "verified") {
      return (
        <div className="text-center py-12">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="h-10 w-10 text-green-600" weight="fill" />
          </div>
          <h2 className="font-heading text-2xl font-bold mb-2">You're Verified!</h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            Your identity has been verified. You now have the verification badge displayed on your profile and listings.
          </p>
          <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-secondary text-white">
            <ShieldCheck className="h-5 w-5" weight="fill" />
            Verified Seller
          </div>
        </div>
      );
    }

    if (user?.verification_status === "pending") {
      return (
        <div className="text-center py-12">
          <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <Clock className="h-10 w-10 text-yellow-600" weight="fill" />
          </div>
          <h2 className="font-heading text-2xl font-bold mb-2">Verification Pending</h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            Your verification documents are being reviewed by our team. This usually takes 1-2 business days.
          </p>
          <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white">
            <Clock className="h-5 w-5" />
            Under Review
          </div>
        </div>
      );
    }

    // Unverified - show form
    return (
      <form onSubmit={handleSubmit}>
        {/* Info */}
        <div className="bg-primary/10 border border-primary/20 p-4 mb-6 flex items-start gap-3">
          <Info className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium">Why get verified?</p>
            <p className="text-muted-foreground">
              Verified sellers get a trust badge, increased visibility, and buyers feel more confident purchasing from you.
            </p>
          </div>
        </div>

        {/* Government ID */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Government-Issued ID
          </label>
          <p className="text-sm text-muted-foreground mb-3">
            Upload a clear photo of your BC driver's license, BC Services Card, or passport.
          </p>
          
          <div className="border-2 border-dashed border-border p-6">
            {governmentIdPreview ? (
              <div className="relative">
                <img
                  src={governmentIdPreview}
                  alt="Government ID"
                  className="max-h-48 mx-auto"
                />
                <button
                  type="button"
                  onClick={() => {
                    setGovernmentId(null);
                    setGovernmentIdPreview(null);
                  }}
                  className="absolute top-0 right-0 p-2 bg-destructive text-white"
                >
                  Remove
                </button>
              </div>
            ) : (
              <label className="flex flex-col items-center cursor-pointer">
                <IdentificationCard className="h-12 w-12 text-muted-foreground mb-3" />
                <span className="text-sm font-medium">Click to upload ID</span>
                <span className="text-xs text-muted-foreground">PNG, JPG up to 5MB</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileChange("id", e)}
                  className="hidden"
                />
              </label>
            )}
          </div>
        </div>

        {/* Selfie */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Selfie Photo
          </label>
          <p className="text-sm text-muted-foreground mb-3">
            Take a clear selfie holding your ID next to your face. Make sure both are clearly visible.
          </p>
          
          <div className="border-2 border-dashed border-border p-6">
            {selfiePreview ? (
              <div className="relative">
                <img
                  src={selfiePreview}
                  alt="Selfie"
                  className="max-h-48 mx-auto"
                />
                <button
                  type="button"
                  onClick={() => {
                    setSelfie(null);
                    setSelfiePreview(null);
                  }}
                  className="absolute top-0 right-0 p-2 bg-destructive text-white"
                >
                  Remove
                </button>
              </div>
            ) : (
              <label className="flex flex-col items-center cursor-pointer">
                <Camera className="h-12 w-12 text-muted-foreground mb-3" />
                <span className="text-sm font-medium">Click to upload selfie</span>
                <span className="text-xs text-muted-foreground">PNG, JPG up to 5MB</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileChange("selfie", e)}
                  className="hidden"
                />
              </label>
            )}
          </div>
        </div>

        {/* Warning */}
        <div className="bg-muted p-4 mb-6 flex items-start gap-3">
          <Warning className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
          <div className="text-sm text-muted-foreground">
            <p>Your documents are securely stored and only used for identity verification purposes. We never share your personal information.</p>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !governmentIdPreview || !selfiePreview}
          className="w-full py-4 bg-primary text-white font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          data-testid="submit-verification"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Upload className="h-5 w-5" />
              Submit for Verification
            </>
          )}
        </button>
      </form>
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <ShieldCheck className="h-8 w-8 text-primary" weight="fill" />
            </div>
            <h1 className="font-heading text-3xl font-bold" data-testid="verification-title">
              Identity Verification
            </h1>
            <p className="text-muted-foreground mt-2">
              Verify your identity to build trust with buyers
            </p>
          </div>

          {/* Content */}
          <div className="bg-white border border-border p-6">
            {renderStatusContent()}
          </div>

          {/* Benefits */}
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border border-border p-4 text-center">
              <ShieldCheck className="h-8 w-8 text-primary mx-auto mb-2" />
              <p className="font-medium text-sm">Trust Badge</p>
              <p className="text-xs text-muted-foreground">Displayed on your profile</p>
            </div>
            <div className="bg-white border border-border p-4 text-center">
              <User className="h-8 w-8 text-primary mx-auto mb-2" />
              <p className="font-medium text-sm">Buyer Confidence</p>
              <p className="text-xs text-muted-foreground">More likely to bid</p>
            </div>
            <div className="bg-white border border-border p-4 text-center">
              <CheckCircle className="h-8 w-8 text-primary mx-auto mb-2" />
              <p className="font-medium text-sm">Priority Support</p>
              <p className="text-xs text-muted-foreground">Faster response times</p>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
