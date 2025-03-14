import streamlit as st
import google.generativeai as genai
import os
from PyPDF2 import PdfReader
import tempfile
import markdown
import re
from io import BytesIO
import time

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListItem, ListFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Configure Gemini API
os.environ["GOOGLE_API_KEY"] = "AIzaSyDvc4O1ES0X2AA92Aw23iZcwgEanwTfqGo"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def extract_text_from_pdf(pdf_file):
    """Extract text content from uploaded PDF file."""
    try:
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

def analyze_resume(text):
    """Use Gemini to analyze and extract key information from resume text."""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""
        Analyze this resume text and extract the following key information:
        - Personal Information (name, contact details)
        - Professional Summary
        - Key Skills
        - Work Experience (most relevant and recent)
        - Education
        - Certifications (if any)
        
        Text: {text}
        
        Format the output in markdown with clear section headers and proper markdown formatting.
        Focus on the most relevant information for a consultant role.
        Use proper markdown syntax for headers (#), lists (-), and emphasis (*).
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error analyzing resume: {e}")
        return None

def analyze_rfp(text):
    """Use Gemini to analyze and extract key requirements from RFP text."""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""
        Analyze this Request for Proposal (RFP) document and extract the most important information required from a consultant profile standpoint.
        
        Focus on extracting:
        - Required qualifications
        - Technical skills needed
        - Domain knowledge requirements
        - Years of experience requirements
        - Certifications required
        - Specific expertise areas
        - Project roles and responsibilities
        - Any other critical requirements for consultants
        
        Text: {text}
        
        Format the output in markdown with clear section headers and proper markdown formatting.
        Use proper markdown syntax for headers (#), lists (-), and emphasis (*).
        Prioritize the most important requirements that would be relevant for matching a consultant profile.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error analyzing RFP: {e}")
        return None

def generate_concise_resume(raw_cv, rfp_requirements=None):
    """Generate a concise 2-page resume using the analyzed information, optionally tailored to RFP requirements."""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Base prompt
        base_prompt = f"""
            You are an expert resume formatter and summarizer, specializing in refining consultant resumes for client evaluation. 
            Your task is to transform the following consultant resume into a concise, high-impact, 2-page version tailored for client review.

            Instructions for Refinement:

            Maximize Impact:
            -Prioritize achievements, quantifiable results, and value delivered over general responsibilities.
            -Highlight client outcomes, project impact, and business value created by the consultant.

            Format Professional Experience:
            -Use ### for company names as section headers
            -Use bullet points (-) for experience details under each company
            -Include dates on the same line as company name in parentheses
            -Example format:
              ### Job Title | Company Name | Start Date - End Date |
              - Achievement 1
              - Achievement 2

            Summarize & Condense:
            -Convert lengthy descriptions into concise, results-driven bullet points.
            -Remove redundant, outdated, or lower-impact details.

            Highlight Core Competencies:
            -Clearly showcase technical skills, industry expertise, methodologies, and soft skills essential for consulting.
            -Group skills into logical categories for easy scanning.
            
            Output Format:
            -Use consistent markdown formatting throughout
            -Ensure company names stand out as distinct sections
            -Maintain proper hierarchy in the document structure
        """
        
        # Add RFP-specific instructions if available
        if rfp_requirements:
            rfp_tailoring = f"""
            RFP Tailoring:
            -The resume should be specifically tailored to match the following RFP requirements:
            
            {rfp_requirements}
            
            -Emphasize experiences, skills, and achievements that directly align with these RFP requirements
            -Reorganize content to highlight the most relevant qualifications first
            -Use terminology and keywords from the RFP where appropriate
            -Ensure that the consultant's qualifications that match the RFP requirements are clearly visible
            """
            base_prompt += rfp_tailoring
        
        # Complete the prompt with the resume content
        complete_prompt = base_prompt + f"""
            Here is the full consultant Resume:

            {raw_cv}
 
            Begin the formatted, condensed 2-page resume below:
        """
        
        response = model.generate_content(complete_prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating concise resume: {e}")
        return None

def clean_markdown(markdown_text):
    """Clean and standardize markdown formatting."""
    # Ensure consistent header formatting
    markdown_text = re.sub(r'^#(?!#)\s*', '# ', markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r'^##(?!#)\s*', '## ', markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r'^###(?!#)\s*', '### ', markdown_text, flags=re.MULTILINE)
    
    # Ensure consistent list formatting
    markdown_text = re.sub(r'^\s*[-*]\s*', '- ', markdown_text, flags=re.MULTILINE)
    
    # Add proper spacing between sections
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
    
    # Remove ```markdown at the start if present
    markdown_text = re.sub(r'^```markdown\s*', '', markdown_text)
    
    return markdown_text

def clean_text_for_download(markdown_text):
    """
    Removes markdown formatting characters (* and #) from text for plain text download
    """
    if not markdown_text:
        return ""
    
    # Remove markdown headings (# symbols)
    text = re.sub(r'^#+\s+', '', markdown_text, flags=re.MULTILINE)
    
    # Remove bold and italic formatting (* symbols)
    text = re.sub(r'\*\*', '', text)  # Remove bold (**)
    text = re.sub(r'\*', '', text)    # Remove italic (*)
    
    # Remove other common markdown elements
    text = re.sub(r'`', '', text)     # Remove code ticks
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Replace links with just the text
    
    return text

def markdown_to_pdf_reportlab(markdown_text):
    """Convert markdown to PDF using ReportLab with enhanced styling for a professional resume."""
    buffer = BytesIO()
    
    # Use letter size with margins optimized for a resume
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=54,  # Slightly reduced margins
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Create a professional color scheme
    primary_color = colors.HexColor('#1a5276')  # Professional dark blue
    secondary_color = colors.HexColor('#2874a6')  # Medium blue
    accent_color = colors.HexColor('#3498db')  # Light blue
    text_color = colors.HexColor('#2c3e50')  # Dark gray-blue for text
    
    # Create custom styles with different names to avoid conflicts
    title_style = ParagraphStyle(
        name='ResumeTitle', 
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20, 
        spaceAfter=10,
        textColor=primary_color,
        alignment=TA_CENTER,
        borderPadding=5,
        borderWidth=0,
        leading=24  # Line height
    )
    
    section_style = ParagraphStyle(
        name='ResumeSection', 
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14, 
        spaceAfter=8,
        spaceBefore=12,
        textColor=primary_color,
        borderColor=primary_color,
        borderWidth=0,
        borderPadding=5,
        borderRadius=0,
        leading=16,
        # Add a bottom border
        endDots=None,
        bulletIndent=0,
        firstLineIndent=0,
        leftIndent=0,
        rightIndent=0
    )
    
    subsection_style = ParagraphStyle(
        name='ResumeSubsection', 
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12, 
        spaceAfter=4,
        spaceBefore=6,
        textColor=secondary_color,
        leading=14,
        leftIndent=0
    )
    
    normal_style = ParagraphStyle(
        name='ResumeNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        spaceAfter=6,
        textColor=text_color,
        leading=14
    )
    
    list_item_style = ParagraphStyle(
        name='ResumeListItem',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leftIndent=10,
        firstLineIndent=-10,  # Hanging indent for bullet points
        textColor=text_color,
        leading=14,
        spaceBefore=2,
        spaceAfter=2
    )
    
    # Parse markdown to ReportLab elements
    elements = []
    
    # Split by lines to process headers and content
    lines = markdown_text.split('\n')
    i = 0
    
    # Add a function to clean text for PDF
    def clean_text_for_pdf(text):
        # Replace markdown bold/italic with actual formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        # Replace backticks with appropriate formatting
        text = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', text)
        return text
    
    # Process the first line as the resume title if it's a level 1 heading
    if lines[0].strip().startswith('# '):
        title_text = clean_text_for_pdf(lines[0].strip()[2:])
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 10))
        i = 1
    
    # Track if we're inside a section to handle spacing
    in_section = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Process headers
        if line.startswith('# '):
            # Main title
            title_text = clean_text_for_pdf(line[2:])
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 10))
            in_section = False
            
        elif line.startswith('## '):
            # Section headers with horizontal rule effect
            section_text = clean_text_for_pdf(line[3:])
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(section_text, section_style))
            # Add a thin horizontal line
            elements.append(Spacer(1, 2))
            elements.append(Paragraph('<hr width="100%" color="{0}" />'.format(primary_color.hexval()[1:]), 
                                     ParagraphStyle(name='HRule', alignment=TA_LEFT)))
            elements.append(Spacer(1, 6))
            in_section = True
            
        elif line.startswith('### '):
            # Subsection headers
            subsection_text = clean_text_for_pdf(line[4:])
            elements.append(Paragraph(subsection_text, subsection_style))
            elements.append(Spacer(1, 4))
            in_section = True
        
        # Process lists
        elif line.startswith('- '):
            # Collect all list items
            list_items = []
            while i < len(lines) and lines[i].strip().startswith('- '):
                item_text = clean_text_for_pdf(lines[i].strip()[2:])
                # Create a custom bullet point
                bullet_para = Paragraph('• ' + item_text, list_item_style)
                list_items.append(bullet_para)
                i += 1
            
            # Add the list items directly (not using ListFlowable for better control)
            for item in list_items:
                elements.append(item)
            
            continue  # Skip the increment at the end since we've already advanced
        
        # Process normal paragraphs
        elif line:
            para_text = clean_text_for_pdf(line)
            elements.append(Paragraph(para_text, normal_style))
            
        # Add a small space for empty lines to maintain structure
        elif i > 0 and i < len(lines) - 1 and not lines[i-1].strip() and lines[i+1].strip():
            if in_section:
                elements.append(Spacer(1, 6))  # Smaller space within sections
            else:
                elements.append(Spacer(1, 10))  # Larger space between major sections
        
        i += 1
    
    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def main():
    # Set page config to wide mode and add custom CSS for full screen
    st.set_page_config(
        page_title="Professional Resume Optimizer",
        page_icon="📄",
        layout="wide"
    )
    
    # Custom CSS to make the app full screen and improve UI
    st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 5rem;
        padding-right: 5rem;
        max-width: 100%;
    }
    .stApp {
        max-width: 100%;
    }
    .st-emotion-cache-16txtl3 {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Professional Resume Optimizer")
    st.write("Upload a consultant's resume and/or an RFP to extract requirements and generate a tailored, optimized resume")
    
    # Initialize session states for tracking processed files and results
    if 'rfp_requirements' not in st.session_state:
        st.session_state.rfp_requirements = None
    if 'rfp_processed' not in st.session_state:
        st.session_state.rfp_processed = False
    if 'resume_analyzed' not in st.session_state:
        st.session_state.resume_analyzed = False
    if 'analyzed_info' not in st.session_state:
        st.session_state.analyzed_info = None
    if 'concise_resume' not in st.session_state:
        st.session_state.concise_resume = None
    if 'cleaned_markdown' not in st.session_state:
        st.session_state.cleaned_markdown = None
    if 'resume_text' not in st.session_state:
        st.session_state.resume_text = None
    if 'pdf_generated' not in st.session_state:
        st.session_state.pdf_generated = False
    if 'pdf_buffer' not in st.session_state:
        st.session_state.pdf_buffer = None
    
    # Create two columns for the file uploaders
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Resume Upload")
        uploaded_resume = st.file_uploader("Upload Resume (PDF format)", type=['pdf'], key="resume_uploader")
        
        # Only show process button if a resume is uploaded
        if uploaded_resume is not None:
            # Extract text from PDF if not already done
            if st.session_state.resume_text is None or uploaded_resume.name != st.session_state.resume_filename:
                st.session_state.resume_text = extract_text_from_pdf(uploaded_resume)
                st.session_state.resume_filename = uploaded_resume.name
                st.session_state.resume_analyzed = False  # Reset analysis flag for new file
                st.session_state.analyzed_info = None
                st.session_state.concise_resume = None
                st.session_state.cleaned_markdown = None
            
            # Process resume button
            if st.button("Process Resume"):
                with st.spinner("Processing resume..."):
                    if st.session_state.resume_text:
                        # Analyze resume content
                        st.subheader("Resume Analysis Progress")
                        progress_bar = st.progress(0)
                        
                        st.session_state.analyzed_info = analyze_resume(st.session_state.resume_text)
                        progress_bar.progress(33)
                        
                        if st.session_state.analyzed_info:
                            # Generate concise resume, using RFP requirements if available
                            st.session_state.concise_resume = generate_concise_resume(
                                st.session_state.resume_text, 
                                rfp_requirements=st.session_state.rfp_requirements
                            )
                            progress_bar.progress(66)
                            
                            if st.session_state.concise_resume:
                                # Clean markdown formatting
                                st.session_state.cleaned_markdown = clean_markdown(st.session_state.concise_resume)
                                progress_bar.progress(100)
                                
                                st.session_state.resume_analyzed = True
                                st.success("Resume processing completed!")
    
    with col2:
        st.subheader("RFP Upload (Optional)")
        uploaded_rfp = st.file_uploader("Upload RFP (PDF format)", type=['pdf'], key="rfp_uploader")
        
        # Only show process button if an RFP is uploaded
        if uploaded_rfp is not None:
            # Extract text from PDF if not already done
            if not st.session_state.rfp_processed or uploaded_rfp.name != st.session_state.rfp_filename:
                st.session_state.rfp_text = extract_text_from_pdf(uploaded_rfp)
                st.session_state.rfp_filename = uploaded_rfp.name
                st.session_state.rfp_processed = False  # Reset processed flag for new file
            
            # Process RFP button
            if st.button("Process RFP"):
                with st.spinner("Processing RFP..."):
                    if st.session_state.rfp_text:
                        st.subheader("RFP Analysis")
                        rfp_progress = st.progress(0)
                        
                        # Analyze RFP content
                        st.session_state.rfp_requirements = analyze_rfp(st.session_state.rfp_text)
                        rfp_progress.progress(100)
                        
                        if st.session_state.rfp_requirements:
                            st.session_state.rfp_processed = True
                            st.success("RFP analysis completed!")
                            
                            # If resume was already analyzed, suggest reprocessing it with the new RFP
                            if st.session_state.resume_analyzed:
                                st.info("You may want to reprocess the resume to tailor it to the new RFP requirements.")
    
    # Create tabs for all features
    # Only show Results section if something has been processed
    if (st.session_state.rfp_processed and st.session_state.rfp_requirements) or \
       (st.session_state.resume_analyzed and st.session_state.cleaned_markdown):
        st.subheader("Results")
        
        # Determine which tabs to show
        tabs_to_show = []
        if st.session_state.rfp_processed and st.session_state.rfp_requirements:
            tabs_to_show.append("RFP Requirements")
        if st.session_state.resume_analyzed and st.session_state.cleaned_markdown:
            # Hide the Markdown Resume tab as requested, but keep the PDF Generator
            # tabs_to_show.append("Markdown Resume")  # Commented out to hide this tab
            tabs_to_show.append("PDF Generator")
        
        # Only show tabs if there are results to display
        if tabs_to_show:
            tabs = st.tabs(tabs_to_show)
            
            # Track the current tab index
            tab_index = 0
            
            # RFP Requirements tab
            if st.session_state.rfp_processed and st.session_state.rfp_requirements:
                with tabs[tab_index]:
                    st.markdown(st.session_state.rfp_requirements)
                    # Clean markdown for download
                    clean_rfp_text = clean_text_for_download(st.session_state.rfp_requirements)
                    st.download_button(
                        label="Download RFP Requirements",
                        data=clean_rfp_text,
                        file_name="rfp_requirements.txt",
                        mime="text/plain"
                    )
                tab_index += 1
            
            # Markdown Resume tab (hidden but functionality remains)
            if st.session_state.resume_analyzed and st.session_state.cleaned_markdown:
                # The content is now outside of any tab, so we don't need to use tabs[tab_index]
                # This content is now hidden from the UI
                
                # We also don't increment tab_index since this tab is hidden
                # Keep the variables and processing for potential future use
                resume_title = "Optimized Resume"
                if st.session_state.rfp_processed and st.session_state.rfp_requirements:
                    resume_title += " (Tailored to RFP)"
                
                # Store these values but don't display them
                clean_resume_text = clean_text_for_download(st.session_state.cleaned_markdown)
                
            # PDF Generator tab
            with tabs[tab_index]:
                st.write("### PDF Generation")
                markdown_editor = st.text_area(
                    "Edit Markdown (if needed):",
                    value=st.session_state.cleaned_markdown,
                    height=400
                )
                
                # Use a form to prevent rerunning the whole app
                with st.form(key="pdf_form"):
                    generate_button = st.form_submit_button("Generate PDF")
                    if generate_button:
                        st.session_state.pdf_buffer = markdown_to_pdf_reportlab(markdown_editor)
                        st.session_state.pdf_generated = True
                
                # Only show download button after PDF is generated
                if st.session_state.pdf_generated and st.session_state.pdf_buffer is not None:
                    st.success("PDF successfully generated!")
                    st.download_button(
                        label="Download PDF",
                        data=st.session_state.pdf_buffer,
                        file_name="optimized_resume.pdf",
                        mime="application/pdf"
                    )

if __name__ == "__main__":
    main()
