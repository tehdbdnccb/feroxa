import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Fixora Kisumu",
    short_name: "Fixora",
    description: "Trusted repair workflow for Apple-device owners in Kisumu.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f5f0",
    theme_color: "#121212",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
