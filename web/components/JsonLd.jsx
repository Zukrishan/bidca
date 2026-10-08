/**
 * schema.org JSON-LD block. Listing titles, descriptions and seller names are user input, so
 * <, > and & are escaped: a value containing "</script>" must not be able to close the tag.
 */
export function JsonLd({ data }) {
  const json = JSON.stringify(data)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026");
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}
