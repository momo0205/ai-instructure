import { GraphDefinition } from '../types';
/**
 * Main generator function
 * Takes a GraphDefinition and returns a .drawio XML string
 */
export declare function generateDrawio(graph: GraphDefinition): string;
/**
 * Validate GraphDefinition - check for required fields
 */
export declare function validateGraph(graph: unknown): {
    valid: boolean;
    errors: string[];
};
//# sourceMappingURL=index.d.ts.map