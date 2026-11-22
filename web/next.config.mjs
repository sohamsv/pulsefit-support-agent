/** @type {import('next').NextConfig} */
const nextConfig = {
  // Tailwind CSS v4 is applied through this Turbopack rule (set up by create-next-app).
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
