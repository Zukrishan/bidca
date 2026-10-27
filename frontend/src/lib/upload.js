import axios from "axios";

/**
 * Upload one image straight to Cloudinary with a signature from the API; resolves the https URL.
 * Throws Error("Photo upload is not available yet") when Cloudinary isn't configured (API 503).
 */
export async function uploadImage(api, file, folder = "bidca_avatars") {
  let sig;
  try {
    ({ data: sig } = await axios.get(`${api}/cloudinary/signature`, { params: { folder, resource_type: "image" } }));
  } catch (err) {
    if (err.response?.status === 503) throw new Error("Photo upload is not available yet");
    throw err;
  }
  const form = new FormData();
  form.append("file", file);
  form.append("api_key", sig.api_key);
  form.append("timestamp", sig.timestamp);
  form.append("signature", sig.signature);
  form.append("folder", sig.folder);
  const res = await fetch(`https://api.cloudinary.com/v1_1/${sig.cloud_name}/image/upload`, { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || !body.secure_url) throw new Error(body.error?.message || "Upload failed");
  return body.secure_url;
}
