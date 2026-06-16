import React from 'react';
import ReactMarkdown from 'react-markdown';

interface AnalysisDisplayProps {
  content: string;
}

const AnalysisDisplay: React.FC<AnalysisDisplayProps> = ({ content }) => {
  return (
    <div className="prose prose-invert prose-sm md:prose-base max-w-none">
      <ReactMarkdown
        components={{
          h1: ({node, ...props}) => <h1 className="text-xl font-bold text-blue-400 mb-4" {...props} />,
          h2: ({node, ...props}) => <h2 className="text-lg font-semibold text-blue-300 mt-6 mb-3" {...props} />,
          h3: ({node, ...props}) => <h3 className="text-md font-medium text-slate-200 mt-4 mb-2" {...props} />,
          strong: ({node, ...props}) => <strong className="text-indigo-300 font-semibold" {...props} />,
          ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-1 text-slate-300" {...props} />,
          li: ({node, ...props}) => <li className="pl-1" {...props} />,
          p: ({node, ...props}) => <p className="mb-4 text-slate-300 leading-relaxed" {...props} />,
          a: ({node, ...props}) => <a className="text-blue-400 hover:underline break-all" target="_blank" rel="noopener noreferrer" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default AnalysisDisplay;