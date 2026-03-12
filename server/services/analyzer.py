"""Analysis orchestrator — coordinates all detectors."""

import asyncio
import json
import logging
import time
import uuid

import httpx

from server.config import settings
from server.detectors.blocking import BlockingDetector
from server.detectors.bot_access import BotAccessDetector
from server.detectors.bot_protection import BotProtectionDetector
from server.detectors.content_signal import ContentSignalDetector
from server.detectors.faq_schema import FaqSchemaDetector
from server.detectors.inventory import InventoryDetector
from server.detectors.markdown_agents import MarkdownAgentsDetector
from server.detectors.meta_tags import MetaTagsDetector
from server.detectors.provider import ProviderDetector
from server.detectors.robots import RobotsDetector
from server.detectors.rsl import RslDetector
from server.detectors.schema_parser import SchemaParser
from server.detectors.sitemap import SitemapDetector
from server.detectors.vdp import VdpDetector
from server.models.responses import AnalysisResponse
from server.scoring.recommendations import generate_recommendations
from server.scoring.scorer import AICompatibilityScorer

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """Coordinates all detection modules for a full site analysis."""

    def __init__(self) -> None:
        self._results: dict[str, AnalysisResponse] = {}
        self._progress: dict[str, dict] = {}

    def get_result(self, analysis_id: str) -> AnalysisResponse | None:
        return self._results.get(analysis_id)

    def get_progress(self, analysis_id: str) -> dict | None:
        return self._progress.get(analysis_id)

    async def start_analysis(self, url: str) -> str:
        """Start analysis in background, return ID immediately."""
        analysis_id = str(uuid.uuid4())[:8]

        # Parse domain
        from server.detectors.base import BaseDetector

        domain = BaseDetector.clean_domain(url)

        self._results[analysis_id] = AnalysisResponse(id=analysis_id, url=url, status="running")
        self._progress[analysis_id] = {"step": "starting", "percent": 0}

        # Launch background task
        asyncio.create_task(self._run_analysis(analysis_id, domain, url))
        return analysis_id

    async def _run_analysis(self, analysis_id: str, domain: str, url: str) -> None:
        """Run full analysis pipeline."""
        start_time = time.time()
        page_cache: dict[str, str] = {}
        analysis_data: dict = {}

        try:
            async with httpx.AsyncClient(
                timeout=settings.request_timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            ) as client:
                # Create detectors with shared client and cache
                blocking_det = BlockingDetector(client, page_cache)
                robots_det = RobotsDetector(client, page_cache)
                bot_access_det = BotAccessDetector(client, page_cache)
                bot_prot_det = BotProtectionDetector(client, page_cache)
                schema_det = SchemaParser(client, page_cache)
                provider_det = ProviderDetector(client, page_cache)
                inventory_det = InventoryDetector(client, page_cache)
                vdp_det = VdpDetector(client, page_cache)
                sitemap_det = SitemapDetector(client, page_cache)
                meta_det = MetaTagsDetector(client, page_cache)
                markdown_det = MarkdownAgentsDetector(client, page_cache)
                content_signal_det = ContentSignalDetector(client, page_cache)
                rsl_det = RslDetector(client, page_cache)
                faq_det = FaqSchemaDetector(client, page_cache)

                # Set start time on all detectors
                for det in [
                    blocking_det,
                    robots_det,
                    bot_access_det,
                    schema_det,
                    provider_det,
                    inventory_det,
                    vdp_det,
                    sitemap_det,
                    meta_det,
                    markdown_det,
                    content_signal_det,
                    rsl_det,
                    faq_det,
                ]:
                    det.set_start_time(start_time)

                # Step 1: Basic access check
                self._update_progress(analysis_id, "Checking site access", 5)
                blocking_info, homepage_resp = await blocking_det.check_access(domain)
                analysis_data["base_analysis"] = {
                    "response_code": blocking_info.status_code,
                    "cloudflare_detected": blocking_info.cloudflare_detected,
                    "js_challenge": blocking_info.js_challenge,
                    "captcha_detected": blocking_info.captcha_detected,
                    "forbidden_access": blocking_info.is_blocked
                    and blocking_info.status_code == 403,
                    "datacenter_blocked": blocking_info.is_blocked
                    and blocking_info.status_code is None,
                    "rate_limited": False,
                }
                analysis_data["cloudflare_present"] = blocking_info.cloudflare_detected

                homepage_content = ""
                if homepage_resp and homepage_resp.text:
                    homepage_content = homepage_resp.text

                site_blocked = blocking_info.is_blocked

                # Step 2: Parallel checks (provider, meta, schema, sitemap, robots)
                self._update_progress(analysis_id, "Analyzing site structure", 15)

                if site_blocked:
                    # Limited checks when blocked
                    (robots_result,) = await asyncio.gather(
                        robots_det.check(domain),
                    )
                    analysis_data["ai_bots"] = {"robots_analysis": robots_result, "access_test": {}}
                    analysis_data["site_blocked"] = True
                    analysis_data["base_analysis"]["cloudflare_blocking_tier"] = (
                        blocking_info.cloudflare_blocking_tier
                    )
                    analysis_data["base_analysis"]["cloudflare_tier_signals"] = (
                        blocking_info.cloudflare_tier_signals
                    )

                    # Live AI verification on blocked sites — discovery mode
                    # Our server is DC-blocked, so AI providers scrape independently
                    if settings.ai_verify_enabled:
                        self._update_progress(
                            analysis_id, "AI discovery scrape (site blocked us)", 40
                        )
                        from server.detectors.ground_truth import GroundTruthCrawler

                        gt_crawler = GroundTruthCrawler(
                            domain=domain,
                            robots_data=robots_result,
                        )
                        ground_truth_result = await gt_crawler.crawl()

                        self._update_progress(
                            analysis_id,
                            "AI providers accessing site independently",
                            55,
                        )
                        from server.detectors.ai_live_verify import AILiveVerifyDetectorV2

                        verify_v2 = AILiveVerifyDetectorV2(
                            domain, ground_truth_result, discovery_mode=True
                        )
                        verify_result_v2 = await verify_v2.verify()
                        analysis_data["ai_live_verify_v2"] = verify_result_v2.model_dump()
                        analysis_data["ai_live_verify"] = verify_result_v2.model_dump()

                        # Classify blocking type based on AI provider results
                        providers = verify_result_v2.providers
                        non_error = [p for p in providers if p.overall_access != "error"]
                        any_accessible = any(
                            p.overall_access in ("full", "partial") for p in non_error
                        )
                        all_blocked = all(
                            p.overall_access == "blocked" for p in non_error
                        ) and len(non_error) > 0

                        if any_accessible:
                            blocking_info.blocking_type = "datacenter_ip"
                        elif all_blocked:
                            blocking_info.blocking_type = "ai_block"

                        analysis_data["base_analysis"]["blocking_type"] = (
                            blocking_info.blocking_type
                        )
                else:
                    # Full parallel analysis
                    (
                        provider_info,
                        homepage_meta,
                        homepage_schema,
                        sitemap_info,
                        robots_result,
                    ) = await asyncio.gather(
                        asyncio.ensure_future(
                            self._detect_provider(provider_det, homepage_content)
                        ),
                        meta_det.check(f"https://{domain}", homepage_content),
                        schema_det.check(domain),
                        sitemap_det.check(domain),
                        robots_det.check(domain),
                    )

                    analysis_data["website_provider"] = {
                        "provider_name": provider_info.name,
                        "confidence": provider_info.confidence,
                    }
                    analysis_data["meta_tags"] = {
                        "homepage": {
                            "title": homepage_meta.title,
                            "description": homepage_meta.description,
                            "meta_description": homepage_meta.description,
                            "canonical": homepage_meta.canonical,
                            "canonical_valid": bool(homepage_meta.canonical),
                            "has_og_tags": homepage_meta.has_og_tags,
                            "og_title": homepage_meta.has_og_tags,
                            "noai_directive": homepage_meta.noai_directive,
                            "noimageai_directive": homepage_meta.noimageai_directive,
                        }
                    }
                    analysis_data["homepage_json_ld"] = homepage_schema
                    analysis_data["sitemap"] = {
                        "sitemap_found": sitemap_info.found,
                        "sitemap_url": sitemap_info.url,
                        "total_urls": sitemap_info.entry_count,
                        "has_vehicle_urls": sitemap_info.entry_count > 0,
                        "sitemap_fresh": sitemap_info.has_lastmod,
                    }

                    # Step 3: Bot protection detection
                    self._update_progress(analysis_id, "Detecting bot protection", 25)
                    bot_prot = bot_prot_det.detect(homepage_content)
                    analysis_data["bot_protection"] = {
                        "bot_protection_detected": bot_prot.detected,
                        "protection_type": bot_prot.vendor,
                    }

                    # Step 4: Inventory + VDP discovery (sequential, depends on provider)
                    self._update_progress(analysis_id, "Finding inventory pages", 35)
                    provider_name = provider_info.name if provider_info.name != "Unknown" else None
                    inv_info = await inventory_det.check(domain, provider_name)
                    analysis_data["inventory_page"] = {
                        "inventory_found": inv_info.found,
                        "inventory_url": inv_info.url,
                        "vehicle_count": inv_info.vehicle_count,
                        "vehicle_count_estimate": inv_info.vehicle_count,
                        "has_itemlist_schema": any(
                            s.schema_type in ("ItemList", "OfferCatalog") for s in inv_info.schemas
                        ),
                        "inventory_json_ld": {
                            "schema_details": [
                                {
                                    "type": s.schema_type,
                                    "properties_found": s.properties_found,
                                    "properties_missing": s.properties_missing,
                                    "completeness_score": s.completeness,
                                }
                                for s in inv_info.schemas
                            ],
                        },
                    }

                    self._update_progress(analysis_id, "Finding vehicle detail pages", 50)
                    # Get sample VDP URLs from sitemap
                    sample_vdps = None  # Would come from sitemap parsing
                    vdp_info = await vdp_det.check(
                        domain, inv_info.url if inv_info.found else None, sample_vdps, provider_name
                    )

                    # Check VDP content
                    vdp_content_info = {}
                    if vdp_info.found and vdp_info.url:
                        vdp_html = await vdp_det.fetch_page(vdp_info.url)
                        if vdp_html:
                            vdp_content_info = vdp_det.check_vdp_content(vdp_html)

                    analysis_data["vdp_page"] = {
                        "vdp_found": vdp_info.found,
                        "vdp_url": vdp_info.url,
                        "has_vehicle_schema": any(
                            s.schema_type
                            in ("Vehicle", "Car", "Product", "IndividualProduct", "Motorcycle")
                            for s in vdp_info.schemas
                        ),
                        "vdp_json_ld": {
                            "schema_details": [
                                {
                                    "type": s.schema_type,
                                    "properties_found": s.properties_found,
                                    "properties_missing": s.properties_missing,
                                    "completeness_score": s.completeness,
                                }
                                for s in vdp_info.schemas
                            ],
                        },
                        "content_in_html": vdp_content_info,
                    }

                    # Step 5: X-Robots-Tag checks
                    self._update_progress(analysis_id, "Checking X-Robots headers", 55)
                    x_robots = {}
                    hp_xr = await meta_det.check_x_robots_header(f"https://{domain}")
                    x_robots["homepage"] = hp_xr
                    if inv_info.found:
                        x_robots["inventory"] = await meta_det.check_x_robots_header(inv_info.url)
                    else:
                        x_robots["inventory"] = {}
                    if vdp_info.found:
                        x_robots["vdp"] = await meta_det.check_x_robots_header(vdp_info.url)
                    else:
                        x_robots["vdp"] = {}
                    analysis_data["x_robots"] = x_robots

                    # Step 6: AI bot access testing
                    self._update_progress(analysis_id, "Testing AI bot access", 65)
                    bot_permissions_list = await bot_access_det.test(
                        domain,
                        robots_result.get("bot_permissions", {}),
                        cloudflare_detected=blocking_info.cloudflare_detected,
                    )

                    # Build access test summary
                    bots_blocked = [
                        b.bot_name for b in bot_permissions_list if b.http_accessible is False
                    ]
                    bots_allowed = [
                        b.bot_name for b in bot_permissions_list if b.http_accessible is True
                    ]
                    bots_cf_whitelisted = [
                        b.bot_name for b in bot_permissions_list if b.cloudflare_ip_whitelisted
                    ]
                    # Classify Cloudflare blocking tier
                    cf_tier, cf_tier_signals = blocking_det.classify_cloudflare_tier(
                        blocking_info.cloudflare_detected, bot_permissions_list
                    )
                    blocking_info.cloudflare_blocking_tier = cf_tier
                    blocking_info.cloudflare_tier_signals = cf_tier_signals
                    analysis_data["base_analysis"]["cloudflare_blocking_tier"] = cf_tier
                    analysis_data["base_analysis"]["cloudflare_tier_signals"] = cf_tier_signals

                    analysis_data["ai_bots"] = {
                        "robots_analysis": robots_result,
                        "access_test": {
                            "bots_blocked": bots_blocked,
                            "bots_allowed": bots_allowed,
                            "bots_cf_whitelisted": bots_cf_whitelisted,
                            "bot_access_results": {
                                b.bot_name: b.http_accessible for b in bot_permissions_list
                            },
                        },
                    }

                    # Step 6.5: Live AI verification (V2 with ground truth)
                    site_is_blocked = (
                        blocking_info.cloudflare_detected
                        or bots_blocked
                        or analysis_data["base_analysis"].get("forbidden_access")
                    )
                    has_vdp_ground_truth = vdp_info.found and vdp_content_info.get("price_text")
                    if settings.ai_verify_enabled and (has_vdp_ground_truth or site_is_blocked):
                        self._update_progress(analysis_id, "Ground truth crawl", 70)

                        # Build ground truth via Playwright (or httpx fallback)
                        from server.detectors.ground_truth import GroundTruthCrawler

                        vdp_urls = [vdp_info.url] if vdp_info.found else []
                        gt_crawler = GroundTruthCrawler(
                            domain=domain,
                            inventory_url=inv_info.url if inv_info.found else "",
                            vdp_urls=vdp_urls,
                            robots_data=robots_result,
                            sitemap_data=analysis_data.get("sitemap"),
                            vdp_content_info=vdp_content_info if has_vdp_ground_truth else None,
                        )
                        ground_truth_result = await gt_crawler.crawl()

                        # V2 AI verification against ground truth
                        self._update_progress(analysis_id, "AI verification (V2)", 75)
                        from server.detectors.ai_live_verify import AILiveVerifyDetectorV2

                        verify_v2 = AILiveVerifyDetectorV2(domain, ground_truth_result)
                        verify_result_v2 = await verify_v2.verify()
                        analysis_data["ai_live_verify_v2"] = verify_result_v2.model_dump()

                        # Also store as ai_live_verify for backwards compat
                        analysis_data["ai_live_verify"] = verify_result_v2.model_dump()

                    # Step 7: v3 new checks (parallel)
                    self._update_progress(analysis_id, "Running v3 checks", 80)
                    robots_content = robots_result.get("raw_robots_txt", "")
                    md_info, cs_info, rsl_info, faq_info = await asyncio.gather(
                        markdown_det.check(domain),
                        content_signal_det.check(domain, robots_content or None),
                        rsl_det.check(domain, robots_content or None),
                        faq_det.check(domain),
                    )
                    analysis_data["markdown_for_agents"] = {
                        "markdown_supported": md_info.available,
                        "available": md_info.available,
                        "token_count": md_info.token_count,
                    }
                    analysis_data["content_signal"] = {
                        "found": cs_info.found,
                        "raw_directive": cs_info.raw_directive,
                    }
                    analysis_data["rsl"] = {
                        "found": rsl_info.found,
                        "license_url": rsl_info.license_url,
                    }
                    analysis_data["faq_schema"] = {
                        "found": faq_info.found,
                        "question_count": faq_info.question_count,
                    }

                    # Rate limiting check (last, to avoid affecting other checks)
                    self._update_progress(analysis_id, "Checking rate limiting", 85)
                    rate_limited = await blocking_det.check_rate_limiting(domain)
                    analysis_data["base_analysis"]["rate_limited"] = rate_limited

                    # Sanity check: if we got schema data, site isn't truly blocked
                    analysis_data["site_blocked"] = False

                # Step 8: Scoring
                self._update_progress(analysis_id, "Calculating score", 95)
                scorer = AICompatibilityScorer()
                score_response, issues = scorer.score(analysis_data)
                recommendations = generate_recommendations(issues, analysis_data)

                # Build final response
                elapsed = round(time.time() - start_time, 1)
                # Build live verify result (V2 or V1)
                ai_live_verify = None
                if "ai_live_verify_v2" in analysis_data:
                    from server.models.schemas import AILiveVerifyResultV2

                    ai_live_verify = AILiveVerifyResultV2(**analysis_data["ai_live_verify_v2"])
                elif "ai_live_verify" in analysis_data:
                    from server.models.schemas import AILiveVerifyResult

                    ai_live_verify = AILiveVerifyResult(**analysis_data["ai_live_verify"])

                response = AnalysisResponse(
                    id=analysis_id,
                    url=url,
                    status="complete",
                    score=score_response,
                    blocking=blocking_info,
                    bot_permissions=bot_permissions_list if not site_blocked else [],
                    bot_protection=bot_prot if not site_blocked else None,
                    inventory=inv_info if not site_blocked else None,
                    vdp=vdp_info if not site_blocked else None,
                    sitemap=sitemap_info if not site_blocked else None,
                    meta_tags=homepage_meta if not site_blocked else None,
                    provider=provider_info if not site_blocked else None,
                    markdown_agents=md_info if not site_blocked else None,
                    content_signal=cs_info if not site_blocked else None,
                    rsl=rsl_info if not site_blocked else None,
                    faq_schema=faq_info if not site_blocked else None,
                    ai_live_verify=ai_live_verify,
                    issues=issues,
                    recommendations=recommendations,
                    analysis_time=elapsed,
                )
                self._results[analysis_id] = response
                self._update_progress(analysis_id, "Complete", 100)
                await self._save_to_db(analysis_id, url, response)

        except Exception as e:
            logger.exception(f"Analysis failed for {domain}")
            error_response = AnalysisResponse(id=analysis_id, url=url, status="error", error=str(e))
            self._results[analysis_id] = error_response
            self._update_progress(analysis_id, "Error", 100)
            await self._save_to_db(analysis_id, url, error_response)

    @staticmethod
    async def _save_to_db(analysis_id: str, url: str, response: AnalysisResponse) -> None:
        """Persist analysis result to the database."""
        try:
            from server.db import execute

            score = response.score.total_score if response.score else None
            grade = response.score.grade if response.score else None
            data_json = json.dumps(response.model_dump(mode="json"))

            await execute(
                """
                INSERT INTO analyses (id, url, score, grade, status, data_json, error)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                ON CONFLICT (id) DO UPDATE SET
                    score = EXCLUDED.score,
                    grade = EXCLUDED.grade,
                    status = EXCLUDED.status,
                    data_json = EXCLUDED.data_json,
                    error = EXCLUDED.error
                """,
                analysis_id,
                url,
                score,
                grade,
                response.status,
                data_json,
                response.error,
            )
        except Exception:
            logger.exception("Failed to save analysis to database")

    @staticmethod
    async def _detect_provider(det: ProviderDetector, content: str):
        """Wrap sync provider detection for gather."""
        return det.detect(content)

    def _update_progress(self, analysis_id: str, step: str, percent: int) -> None:
        self._progress[analysis_id] = {"step": step, "percent": percent}
