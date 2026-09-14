import React from 'react';

interface SafeHtmlPreviewProps {
  htmlContent: string;
}

/**
 * Renders untrusted generated HTML in an isolated execution boundary.
 * 
 * Security Controls (PRD FR-36, Architecture §12):
 * 1. Bare sandbox attribute (sandbox="") — NO allow-scripts, NO allow-same-origin.
 * 2. Opaque null origin: Blocks access to window.parent, cookies, localStorage, and parent DOM.
 * 3. Script execution is completely disabled by browser sandbox enforcement.
 */
export const SafeHtmlPreview: React.FC<SafeHtmlPreviewProps> = ({ htmlContent }) => {
  return (
    <div className="w-full h-full flex flex-col bg-white">
      <iframe
        sandbox=""
        srcDoc={htmlContent}
        className="w-full h-full border-0"
        title="Sandboxed Artifact Preview"
      />
    </div>
  );
};
