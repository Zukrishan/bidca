import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, API, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import axios from "axios";
import {
  Gavel,
  EnvelopeSimple,
  Lock,
  User,
  MapPin,
  ArrowRight,
  Warning
} from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    city: "",
    postal_code: ""
  });
  const [cities, setCities] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCities();
  }, []);

  const fetchCities = async () => {
    try {
      const { data } = await axios.get(`${API}/cities`);
      setCities(data.cities || []);
    } catch (error) {
      console.error("Error fetching cities:", error);
    }
  };

  const validatePostalCode = (code) => {
    const cleaned = code.toUpperCase().replace(/\s/g, "");
    if (cleaned.length !== 6) return false;
    return cleaned.startsWith("V");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    if (!validatePostalCode(formData.postal_code)) {
      setError("Only British Columbia postal codes are accepted (starting with V)");
      return;
    }

    setLoading(true);

    try {
      await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        city: formData.city,
        postal_code: formData.postal_code
      });
      toast.success("Account created successfully!");
      navigate("/dashboard");
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 mb-4">
              <Gavel className="h-10 w-10 text-primary" weight="fill" />
              <span className="font-heading font-bold text-2xl">
                <span className="text-primary">Bid</span>
                <span className="text-secondary">Ca</span>
                <span className="text-muted-foreground">.ca</span>
              </span>
            </div>
            <h1 className="font-heading text-2xl font-bold" data-testid="register-title">
              Create Your Account
            </h1>
            <p className="text-muted-foreground mt-2">
              Join BC's trusted auction community
            </p>
          </div>

          {/* BC Only Notice */}
          <div className="mb-6 p-4 bg-primary/10 border border-primary/20 flex items-start gap-3">
            <MapPin className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" weight="fill" />
            <div className="text-sm">
              <p className="font-medium text-foreground">BC Residents Only</p>
              <p className="text-muted-foreground">This platform is exclusively for British Columbia residents.</p>
            </div>
          </div>

          {/* Form */}
          <div className="bg-white border border-border p-8">
            {error && (
              <div className="mb-6 p-4 bg-destructive/10 border border-destructive text-destructive text-sm flex items-start gap-2" data-testid="register-error">
                <Warning className="h-5 w-5 flex-shrink-0" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="full_name">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <input
                    id="full_name"
                    type="text"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    className="w-full pl-10 pr-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
                    placeholder="John Doe"
                    required
                    data-testid="register-name"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="email">
                  Email Address
                </label>
                <div className="relative">
                  <EnvelopeSimple className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full pl-10 pr-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
                    placeholder="you@example.com"
                    required
                    data-testid="register-email"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2" htmlFor="city">
                    City
                  </label>
                  <select
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
                    required
                    data-testid="register-city"
                  >
                    <option value="">Select city</option>
                    {cities.map((city) => (
                      <option key={city} value={city}>{city}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2" htmlFor="postal_code">
                    Postal Code
                  </label>
                  <input
                    id="postal_code"
                    type="text"
                    value={formData.postal_code}
                    onChange={(e) => setFormData({ ...formData, postal_code: e.target.value.toUpperCase() })}
                    className="w-full px-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
                    placeholder="V6B 1A1"
                    maxLength={7}
                    required
                    data-testid="register-postal"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="password">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full pl-10 pr-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
                    placeholder="••••••••"
                    minLength={6}
                    required
                    data-testid="register-password"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="confirmPassword">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <input
                    id="confirmPassword"
                    type="password"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    className="w-full pl-10 pr-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
                    placeholder="••••••••"
                    required
                    data-testid="register-confirm-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-primary text-white font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                data-testid="register-submit"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="h-5 w-5" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 text-center text-sm">
              <span className="text-muted-foreground">Already have an account?</span>{" "}
              <Link to="/login" className="text-primary font-medium hover:underline" data-testid="login-link">
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
