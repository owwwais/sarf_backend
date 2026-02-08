-- SmartBudget AI Phase 2 Schema Migration
-- SMS/OCR Transaction Ingestion with AI
-- Run this in Supabase SQL Editor AFTER schema.sql

-- 1. Pending Transactions (Inbox for review)
CREATE TABLE IF NOT EXISTS public.pending_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    raw_text TEXT NOT NULL,
    source VARCHAR(20) NOT NULL CHECK (source IN ('sms', 'ocr', 'clipboard')),
    parsed_payee TEXT,
    parsed_amount DECIMAL(12, 2),
    parsed_date DATE,
    suggested_account_id UUID REFERENCES public.accounts(id) ON DELETE SET NULL,
    suggested_category_id UUID REFERENCES public.categories(id) ON DELETE SET NULL,
    confidence_score DECIMAL(3, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'auto_approved')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Payee Embeddings for Semantic Search
CREATE TABLE IF NOT EXISTS public.payee_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    payee_name TEXT NOT NULL,
    category_id UUID REFERENCES public.categories(id) ON DELETE SET NULL,
    embedding vector(1536),
    usage_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, payee_name)
);

-- 3. SMS Patterns for bank detection
CREATE TABLE IF NOT EXISTS public.sms_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_name TEXT NOT NULL,
    pattern_regex TEXT NOT NULL,
    country_code VARCHAR(3) DEFAULT 'SAU',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert common Saudi bank SMS patterns
INSERT INTO public.sms_patterns (bank_name, pattern_regex, country_code) VALUES
('Al Rajhi Bank', 'الراجحي|AlRajhi|ALRAJHI', 'SAU'),
('SNB', 'الأهلي|SNB|NCB', 'SAU'),
('Riyad Bank', 'رياض|Riyad|RIBL', 'SAU'),
('Al Bilad Bank', 'البلاد|AlBilad', 'SAU'),
('SABB', 'ساب|SABB', 'SAU'),
('Al Inma Bank', 'الإنماء|Alinma', 'SAU'),
('Arab National Bank', 'العربي|ANB', 'SAU'),
('STC Pay', 'STC Pay|stcpay', 'SAU'),
('mada', 'مدى|mada', 'SAU')
ON CONFLICT DO NOTHING;

-- Indexes for Phase 2 tables
CREATE INDEX IF NOT EXISTS idx_pending_transactions_user_id ON public.pending_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_pending_transactions_status ON public.pending_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payee_embeddings_user_id ON public.payee_embeddings(user_id);

-- Vector similarity search index (requires pgvector)
CREATE INDEX IF NOT EXISTS idx_payee_embeddings_vector ON public.payee_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- RLS for pending_transactions
ALTER TABLE public.pending_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own pending transactions" ON public.pending_transactions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own pending transactions" ON public.pending_transactions
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own pending transactions" ON public.pending_transactions
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own pending transactions" ON public.pending_transactions
    FOR DELETE USING (auth.uid() = user_id);

-- RLS for payee_embeddings
ALTER TABLE public.payee_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own payee embeddings" ON public.payee_embeddings
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own payee embeddings" ON public.payee_embeddings
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own payee embeddings" ON public.payee_embeddings
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own payee embeddings" ON public.payee_embeddings
    FOR DELETE USING (auth.uid() = user_id);

-- Trigger for updated_at
CREATE TRIGGER update_pending_transactions_updated_at BEFORE UPDATE ON public.pending_transactions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION match_payee_embedding(
    query_embedding vector(1536),
    match_user_id UUID,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    payee_name TEXT,
    category_id UUID,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.id,
        pe.payee_name,
        pe.category_id,
        1 - (pe.embedding <=> query_embedding) AS similarity
    FROM public.payee_embeddings pe
    WHERE pe.user_id = match_user_id
        AND 1 - (pe.embedding <=> query_embedding) > match_threshold
    ORDER BY pe.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
