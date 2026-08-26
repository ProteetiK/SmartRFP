SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 229 (class 1259 OID 16484)
-- Name: audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    rfp_id integer,
    action character varying,
    actor character varying,
    detail text,
    "timestamp" character varying
);


ALTER TABLE public.audit_log OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 16483)
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.audit_log_id_seq OWNER TO postgres;

--
-- TOC entry 3388 (class 0 OID 0)
-- Dependencies: 228
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- TOC entry 223 (class 1259 OID 16442)
-- Name: draft_sections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.draft_sections (
    id integer NOT NULL,
    rfp_id integer,
    section_title character varying,
    content text,
    source text,
    flag_type character varying,
    flag_note text,
    confidence character varying
);


ALTER TABLE public.draft_sections OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16441)
-- Name: draft_sections_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.draft_sections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.draft_sections_id_seq OWNER TO postgres;

--
-- TOC entry 3389 (class 0 OID 0)
-- Dependencies: 222
-- Name: draft_sections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.draft_sections_id_seq OWNED BY public.draft_sections.id;


--
-- TOC entry 227 (class 1259 OID 16470)
-- Name: evaluation_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.evaluation_metrics (
    id integer NOT NULL,
    rfp_id integer,
    proposal_completeness double precision,
    average_confidence double precision,
    context_coverage double precision,
    hallucination_flags integer,
    pricing_freshness double precision,
    sections_generated integer,
    requirements_extracted integer,
    runtime_seconds double precision,
    knowledge_documents integer,
    retrieved_docs_count integer,
    pricing_items integer,
    llm_calls integer,
    demo_mode integer,
    faithfulness double precision,
    answer_relevancy double precision,
    context_precision double precision,
    context_recall double precision,
    mrr double precision,
    hit_rate double precision,
    chunk_overlap double precision,
    evaluated_at character varying,
    ragas_faithfulness double precision,
    ragas_answer_relevancy double precision,
    ragas_context_precision double precision,
    ragas_context_recall double precision,
    ragas_evaluated_at character varying,
    ragas_status character varying,
    ragas_error character varying,
    ragas_attempts integer,
    below_threshold integer,
    threshold_notes character varying,
    stage_latencies_json character varying,
    quality_completeness double precision
);


ALTER TABLE public.evaluation_metrics OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 16469)
-- Name: evaluation_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.evaluation_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.evaluation_metrics_id_seq OWNER TO postgres;

--
-- TOC entry 3390 (class 0 OID 0)
-- Dependencies: 226
-- Name: evaluation_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.evaluation_metrics_id_seq OWNED BY public.evaluation_metrics.id;


--
-- TOC entry 217 (class 1259 OID 16409)
-- Name: knowledge_base; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.knowledge_base (
    id integer NOT NULL,
    title character varying,
    doc_type character varying,
    content text,
    pinecone_indexed integer
);


ALTER TABLE public.knowledge_base OWNER TO postgres;

--
-- TOC entry 216 (class 1259 OID 16408)
-- Name: knowledge_base_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.knowledge_base_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.knowledge_base_id_seq OWNER TO postgres;

--
-- TOC entry 3391 (class 0 OID 0)
-- Dependencies: 216
-- Name: knowledge_base_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.knowledge_base_id_seq OWNED BY public.knowledge_base.id;


--
-- TOC entry 225 (class 1259 OID 16456)
-- Name: pricing; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pricing (
    id integer NOT NULL,
    rfp_id integer,
    item character varying,
    qty character varying,
    unit_price double precision,
    total double precision,
    fetched_at character varying,
    source character varying,
    stale integer
);


ALTER TABLE public.pricing OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16455)
-- Name: pricing_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pricing_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pricing_id_seq OWNER TO postgres;

--
-- TOC entry 3392 (class 0 OID 0)
-- Dependencies: 224
-- Name: pricing_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pricing_id_seq OWNED BY public.pricing.id;


--
-- TOC entry 221 (class 1259 OID 16428)
-- Name: requirements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.requirements (
    id integer NOT NULL,
    rfp_id integer,
    section character varying,
    text text
);


ALTER TABLE public.requirements OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16427)
-- Name: requirements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.requirements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.requirements_id_seq OWNER TO postgres;

--
-- TOC entry 3393 (class 0 OID 0)
-- Dependencies: 220
-- Name: requirements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.requirements_id_seq OWNED BY public.requirements.id;


--
-- TOC entry 219 (class 1259 OID 16418)
-- Name: resource_rates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.resource_rates (
    id integer NOT NULL,
    role character varying(100) NOT NULL,
    experience_level character varying(50) NOT NULL,
    location character varying(100) NOT NULL,
    monthly_rate numeric(12,2) NOT NULL,
    hourly_rate numeric(12,2) NOT NULL,
    currency character varying(10),
    active boolean,
    effective_from date,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.resource_rates OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 16417)
-- Name: resource_rates_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.resource_rates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.resource_rates_id_seq OWNER TO postgres;

--
-- TOC entry 3394 (class 0 OID 0)
-- Dependencies: 218
-- Name: resource_rates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.resource_rates_id_seq OWNED BY public.resource_rates.id;


--
-- TOC entry 215 (class 1259 OID 16399)
-- Name: rfps; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rfps (
    id integer NOT NULL,
    deal_name character varying NOT NULL,
    client_name character varying,
    region character varying,
    deadline character varying,
    contact_email character varying,
    notes text,
    file_name character varying,
    raw_text text,
    status character varying,
    assigned_role character varying,
    assigned_to character varying,
    num_requirements integer,
    num_flags integer,
    use_web_search integer,
    error_message text,
    created_at character varying,
    updated_at character varying
);


ALTER TABLE public.rfps OWNER TO postgres;

--
-- TOC entry 214 (class 1259 OID 16398)
-- Name: rfps_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.rfps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rfps_id_seq OWNER TO postgres;

--
-- TOC entry 3395 (class 0 OID 0)
-- Dependencies: 214
-- Name: rfps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.rfps_id_seq OWNED BY public.rfps.id;


--
-- TOC entry 3217 (class 2604 OID 16487)
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- TOC entry 3214 (class 2604 OID 16445)
-- Name: draft_sections id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.draft_sections ALTER COLUMN id SET DEFAULT nextval('public.draft_sections_id_seq'::regclass);


--
-- TOC entry 3216 (class 2604 OID 16473)
-- Name: evaluation_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evaluation_metrics ALTER COLUMN id SET DEFAULT nextval('public.evaluation_metrics_id_seq'::regclass);


--
-- TOC entry 3209 (class 2604 OID 16412)
-- Name: knowledge_base id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_base ALTER COLUMN id SET DEFAULT nextval('public.knowledge_base_id_seq'::regclass);


--
-- TOC entry 3215 (class 2604 OID 16459)
-- Name: pricing id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pricing ALTER COLUMN id SET DEFAULT nextval('public.pricing_id_seq'::regclass);


--
-- TOC entry 3213 (class 2604 OID 16431)
-- Name: requirements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.requirements ALTER COLUMN id SET DEFAULT nextval('public.requirements_id_seq'::regclass);


--
-- TOC entry 3210 (class 2604 OID 16421)
-- Name: resource_rates id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resource_rates ALTER COLUMN id SET DEFAULT nextval('public.resource_rates_id_seq'::regclass);


--
-- TOC entry 3208 (class 2604 OID 16402)
-- Name: rfps id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rfps ALTER COLUMN id SET DEFAULT nextval('public.rfps_id_seq'::regclass);


--
-- TOC entry 3235 (class 2606 OID 16491)
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- TOC entry 3229 (class 2606 OID 16449)
-- Name: draft_sections draft_sections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.draft_sections
    ADD CONSTRAINT draft_sections_pkey PRIMARY KEY (id);


--
-- TOC entry 3233 (class 2606 OID 16477)
-- Name: evaluation_metrics evaluation_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evaluation_metrics
    ADD CONSTRAINT evaluation_metrics_pkey PRIMARY KEY (id);


--
-- TOC entry 3222 (class 2606 OID 16416)
-- Name: knowledge_base knowledge_base_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_base
    ADD CONSTRAINT knowledge_base_pkey PRIMARY KEY (id);


--
-- TOC entry 3231 (class 2606 OID 16463)
-- Name: pricing pricing_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pricing
    ADD CONSTRAINT pricing_pkey PRIMARY KEY (id);


--
-- TOC entry 3227 (class 2606 OID 16435)
-- Name: requirements requirements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.requirements
    ADD CONSTRAINT requirements_pkey PRIMARY KEY (id);


--
-- TOC entry 3225 (class 2606 OID 16425)
-- Name: resource_rates resource_rates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resource_rates
    ADD CONSTRAINT resource_rates_pkey PRIMARY KEY (id);


--
-- TOC entry 3220 (class 2606 OID 16406)
-- Name: rfps rfps_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rfps
    ADD CONSTRAINT rfps_pkey PRIMARY KEY (id);


--
-- TOC entry 3223 (class 1259 OID 16426)
-- Name: ix_resource_rates_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_resource_rates_id ON public.resource_rates USING btree (id);


--
-- TOC entry 3218 (class 1259 OID 16407)
-- Name: ix_rfps_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_rfps_id ON public.rfps USING btree (id);


--
-- TOC entry 3240 (class 2606 OID 16492)
-- Name: audit_log audit_log_rfp_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_rfp_id_fkey FOREIGN KEY (rfp_id) REFERENCES public.rfps(id);


--
-- TOC entry 3237 (class 2606 OID 16450)
-- Name: draft_sections draft_sections_rfp_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.draft_sections
    ADD CONSTRAINT draft_sections_rfp_id_fkey FOREIGN KEY (rfp_id) REFERENCES public.rfps(id);


--
-- TOC entry 3239 (class 2606 OID 16478)
-- Name: evaluation_metrics evaluation_metrics_rfp_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evaluation_metrics
    ADD CONSTRAINT evaluation_metrics_rfp_id_fkey FOREIGN KEY (rfp_id) REFERENCES public.rfps(id);


--
-- TOC entry 3238 (class 2606 OID 16464)
-- Name: pricing pricing_rfp_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pricing
    ADD CONSTRAINT pricing_rfp_id_fkey FOREIGN KEY (rfp_id) REFERENCES public.rfps(id);


--
-- TOC entry 3236 (class 2606 OID 16436)
-- Name: requirements requirements_rfp_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.requirements
    ADD CONSTRAINT requirements_rfp_id_fkey FOREIGN KEY (rfp_id) REFERENCES public.rfps(id);