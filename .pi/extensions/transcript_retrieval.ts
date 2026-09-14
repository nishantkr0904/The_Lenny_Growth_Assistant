/**
 * Project-local Pi Coding Agent extension registering the transcript_retrieval tool.
 * Binds Pi to the Lenny Growth Assistant retrieval and deterministic grounding layer.
 */

import { Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

export const transcriptRetrievalTool = defineTool({
	name: "transcript_retrieval",
	label: "Transcript Retrieval",
	description:
		"Searches the Lenny Podcast transcript corpus and returns source-grounded evidence. " +
		"Use the returned evidence as the sole factual basis for answers. " +
		"Do not rely on unsupported external knowledge or fabricate statements.",
	parameters: Type.Object({
		query: Type.String({
			description: "Natural language search query regarding product, growth, or advice from podcast guests.",
		}),
		top_k: Type.Optional(
			Type.Number({
				description: "Maximum number of candidate evidence chunks to retrieve (default: 5).",
			}),
		),
	}),

	async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
		const endpoint = process.env.RETRIEVAL_API_URL || "http://localhost:8000/api/v1/retrieval/search";

		try {
			const response = await fetch(endpoint, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					query: params.query,
					top_k: params.top_k || 5,
				}),
			});

			if (!response.ok) {
				const errorDetail = await response.text();
				return {
					content: [
						{
							type: "text",
							text: `Retrieval service error (${response.status}): ${errorDetail}`,
						},
					],
					details: { status: response.status, error: errorDetail },
				};
			}

			const data = await response.json();
			const decision = data.decision;

			if (!decision.can_synthesize || decision.tier === "Insufficient") {
				const insufficientXml = [
					`<retrieved_evidence status="INSUFFICIENT" tier="${decision.tier}" can_synthesize="false" top_score="${decision.top_score}">`,
					`  <grounding_decision>${decision.reason}</grounding_decision>`,
					`  <system_directive>`,
					`    NO_GROUNDED_EVIDENCE: The retrieved evidence does not meet the minimum relevance threshold for factual synthesis.`,
					`    You are strictly FORBIDDEN from answering using general knowledge or fabricating quotes.`,
					`    You MUST explicitly inform the user that this topic is not discussed in Lenny's Podcast transcripts.`,
					`  </system_directive>`,
					`</retrieved_evidence>`,
				].join("\n");

				return {
					content: [{ type: "text", text: insufficientXml }],
					details: {
						tier: decision.tier,
						can_synthesize: false,
						top_score: decision.top_score,
						reason: decision.reason,
					},
				};
			}

			const qualifyingChunks = decision.selected_evidence || [];
			const formattedChunks = qualifyingChunks
				.map((chunk: any) =>
					[
						`  <chunk id="${chunk.chunk_id}" guest="${chunk.guest}" episode="${chunk.title}" score="${chunk.similarity_score}" citation="${chunk.source_identifier}">`,
						`    <speaker>${chunk.speaker || chunk.guest}</speaker>`,
						`    <content>\n${chunk.content.trim()}\n    </content>`,
						`  </chunk>`,
					].join("\n"),
				)
				.join("\n");

			let conflictDirective = "";
			if (decision.tier === "Conflicting") {
				conflictDirective =
					"  <conflict_directive>\n    Notice: Multiple divergent viewpoints were detected across distinct guests. Synthesis must present both perspectives.\n  </conflict_directive>\n";
			}

			const validXml = [
				`<retrieved_evidence status="VALID" tier="${decision.tier}" can_synthesize="true" top_score="${decision.top_score}">`,
				`  <grounding_decision>${decision.reason}</grounding_decision>`,
				conflictDirective,
				`  <system_directive>`,
				`    Use ONLY the factual information in the chunks below.`,
				`    Attribute factual claims to the speaker/guest and reference the episode title.`,
				`  </system_directive>`,
				formattedChunks,
				`</retrieved_evidence>`,
			]
				.filter(Boolean)
				.join("\n");

			return {
				content: [{ type: "text", text: validXml }],
				details: {
					tier: decision.tier,
					can_synthesize: true,
					top_score: decision.top_score,
					chunk_count: qualifyingChunks.length,
					guests: decision.source_diversity?.guests || [],
				},
			};
		} catch (err: any) {
			return {
				content: [
					{
						type: "text",
						text: `Failed to connect to retrieval endpoint at ${endpoint}: ${err.message}`,
					},
				],
				details: { error: err.message },
			};
		}
	},
});

export default function (pi: ExtensionAPI) {
	pi.registerTool(transcriptRetrievalTool);
}
