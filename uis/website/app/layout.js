export const metadata = {
  title: "HealthCore | Web publica",
  description: "Web publica de HealthCore",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}