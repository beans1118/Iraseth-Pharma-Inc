"""Curated transcription of the reviewed 15-page brochure, never an inventory seed.

All identifiers below are review keys, NOT invented product SKUs. Render pages
first with review_brochure.py. This script writes documentation only; no MongoDB.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'docs' / 'brochure'
PDF = FOLDER / 'Core Product A5 (2).pdf'
rows = []


def add(name, page, category, description='', features=(), specs=(), brand=None, kind='individual', notes=(), images=()):
    item = {'candidate_id': f'p{page:02}-' + hashlib.sha256(name.encode()).hexdigest()[:12],
        'name': name, 'description': description, 'category': category,
        'documented_brand': brand, 'documented_manufacturer': None,
        'key_features': list(features), 'specifications': [{'label':k,'value':v} for k,v in specs],
        'source_pdf_page': page, 'source_panel': 'See rendered page and extracted text',
        'candidate_type': kind, 'status': 'Needs Review', 'sku': None, 'unit': None,
        'gaps': ['Staff-assigned SKU required', 'Selling unit requires staff approval'],
        'review_notes': list(notes), 'image_paths': list(images),
        'image_review_status': 'Identified source image; staff approval required' if images else 'No individually verified image assigned',
        'importable': kind in ('individual','documented_variant'), 'approved': False}
    if kind in ('product_family','equipment_family','service_or_offering'):
        item['gaps'].append('Family/offering must be resolved to an individual sellable product with documented model/variant; add independently after verification')
    rows.append(item)
    return item


def variant(parent, name, specs=(), notes=(), images=()):
    row = add(name,parent['source_pdf_page'],parent['category'],parent['description'],parent['key_features'],
        [(s['label'],s['value']) for s in parent['specifications']]+list(specs), parent['documented_brand'],
        'documented_variant', list(parent['review_notes'])+list(notes), images)
    row['family'] = parent['name']
    return row


alpha = add('Alpha Care Adult Diaper',3,'Adult Care','Adult diaper.',
    ['Comfortable soft non-woven fabric','Large and portable'],brand='Alpha Care',kind='product_family',
    notes=['Packaging shows XL and 10 pieces. No other size may be inferred. Promotional safety-guaranteed claim requires staff substantiation.'],images=['images/alpha-care-adult-diaper.png'])
variant(alpha,'Alpha Care Adult Diaper - XL',[('Size shown','XL'),('Packaging shown','10 pieces')],images=alpha['image_paths'])
under = add('Alpha Care Underpads',3,'Adult Care','Bed-protection underpads.',
    ['Advanced bed protection','Super absorbent fluff fill layers','Multipurpose support','Avoid messy puddles or irritations'],brand='Alpha Care',kind='product_family',
    notes=['Dimensions and count are visible on packaging. Promotional safety-guaranteed claim requires staff substantiation.'],images=['images/alpha-care-underpads-front.png','images/alpha-care-underpads-side.png'])
variant(under,'Alpha Care Underpads - 60 cm x 90 cm',[('Dimensions shown','60 cm x 90 cm'),('Packaging shown','10 pieces')],images=under['image_paths'])
glucose=add('Glucoseth',4,'Glucose Monitoring','Blood glucose monitoring kit.',
    ['Kit contains glucose meter, one vial of 10 test strips, 10 lancets, lancing device, manual, warranty and carrying case'],
    [('Blood sample','Capillary blood'),('Blood volume','0.5 microlitre'),('HCT range','20%-60%'),('Measuring range','20-600 mg/dL (1.1-33.3 mmol/L)'),
     ('Measuring unit','mg/dL and mmol/L (switch key)'),('Measuring time','5 seconds'),('Memory','180 results'),('Display','LCD'),
     ('Operating temperature','10-40 degrees C'),('Operating humidity','<85%'),('Storage temperature','0-50 degrees C'),('Storage humidity','<95%'),('Data output','RS232')],
    brand='Glucoseth',notes=['UNRELATED PARAGRAPH: large-capacity refrigerated centrifuge text must not describe Glucoseth.',
    'POWER CONFLICT: table says 2 AAA batteries; kit list says lithium (3.0 V) battery. Both are quarantined pending staff verification.'],images=['images/glucoseth-kit.png'])
polyvol=add('Polyvol',4,'Infusion and Transfusion','Measured volume fluid administration set (burette set).',
    ['Sterile volumetric infusion set with calibrated durable/elastic burette chamber','Bacteria-retentive air inlet on spike',
     'Automatic shut-off valve prevents entry of air when the chamber empties and indicates fluid level','Soft and kink-resistant tubing',
     'One roller clamp after air-vent spike; one roller clamp and one pinch clamp after burette chamber','Needleless Y-port','DEHP free; latex free',
     'Hook protects against accidental pulling from the IV bottle and holds the chamber','Easy roller-clamp regulation','Auto-stop feature when IV fluid is consumed'],
    [('Burette capacity','150 ml'),('Graduation','10 ml'),('Drop factor','Approximately 60 drops/ml'),('Fluid filter','15 micron'),('Tip','Luer lock with cap')],
    brand='POLYMED',images=['images/polyvol.png'])
auto=add('Autofusion Set',5,'Infusion and Transfusion','IV infusion set with auto air stop and priming filter.',
    ['Auto Air Stop filter prevents air entering the line when the IV bottle is empty','Maintains constant fluid level',
     'Priming filter fills the line automatically and maintains a closed system','Reduces IV-fluid spillage and wastage',
     'Clear spike compatible with IV bottles','Grip ring in drip chamber','PVC-free flexible drip chamber','DEHP-free tubing'],
    [('Drop rate','20 drops/ml'),('Infusion compatibility','Gravity feed and pressure infusions up to 2 bars'),('Standard tube length','180 cm')],
    brand='POLYMED',notes=['Brochure claim of reducing healthcare-associated infections requires staff review. Y-port / back-check-valve options must not be assumed to be one combined configuration.'],images=['images/autofusion.png'])
variant(auto,'Autofusion Set - Y Injection Port',[('Option','Latex-free Y injection port')])
variant(auto,'Autofusion Set - Back Check Valve',[('Option','Back check valve')])
micro=add('Microfusion Set',5,'Infusion and Transfusion','IV infusion set with micro drip for paediatric use.',
    ['Transparent flexible drip chamber','Soft, kink-resistant PVC tubing','Smooth roller clamp for controlled fluid-rate adjustment',
     'Latex-free Y injection port for intermittent medication','DEHP free; latex free'],
    [('Drop factor','Approximately 60 drops/ml'),('Fluid filter','15 micron in drip chamber'),('Standard tube length','150 cm'),('Tube inner diameter','3 mm'),('Tube outer diameter','4.1 mm')],brand='POLYMED',images=['images/microfusion.png'])
onco=add('Oncofusion Set',6,'Infusion and Transfusion','IV infusion set with 0.2 micron in-line filter.',
    ['In-line filter prevents particles, air, bacteria and fungi passing into the venous system','Hydrophobic priming-filter cap prevents fluid leakage',
     'Indicated for infusion of chemotherapy drugs','Rotating luer lock','Latex-free Y injection port for intermittent medication','Needle-free Y-site','Latex free; DEHP free; PVC free'],
    [('In-line filter','0.2 micron')],brand='POLYMED',notes=['With/without needle variants are stated; photographed configurations do not identify a precise variant SKU.'],images=['images/oncofusion.png'])
variant(onco,'Oncofusion Set - With Needle',[('Needle option','With needle')])
variant(onco,'Oncofusion Set - Without Needle',[('Needle option','Without needle')])
photo=add('Photofusion Set',6,'Infusion and Transfusion','IV infusion set for photosensitive drugs.',
    ['Protects light-sensitive drugs from UV exposure','UV-resistant tubing minimizes decomposition of active ingredients',
     'Hydrophobic priming-filter cap prevents fluid leakage','Latex free; DEHP free'],brand='POLYMED',images=['images/photofusion.png'])
blood=add('Blood Administration Set',7,'Infusion and Transfusion','For transfusion of blood or blood components.',
    ['Transparent flexible drip chamber','Soft kink-resistant PVC tubing','Lightweight ball facilitates auto shut-off','DEHP free'],
    [('Drop factor','Approximately 20 drops/ml'),('Blood filter','200 micron')],brand='POLYMED',images=['images/blood-administration.png'])
variant(blood,'Blood Administration Set - Priming Filter',[('Option','Priming filter')])
add('Haemofusor Set',7,'Infusion and Transfusion','Blood administration set with airvent and priming filter.',
    ['Priming filter allows automatic filling and maintains a closed system until connected','Latex-free Y injection port'],brand='POLYMED',images=['images/haemofusor.png'])
cannula_features=['Tapered kink-resistant radiopaque catheter','Rounded needle-hub grip for support during insertion','Transparent flashback chamber','Injection port with non-return silicone valve','Flexible wings for secure fixation']
polyflex=add('Polyflex',8,'IV Cannulas','IV cannula with port, snap-fit cap and perforated wings.',cannula_features,
    [('Standard catheter','FEP'),('Optional catheter','PUR'),('Documented size range','14G to 26G')],brand='POLYMED',kind='product_family',images=['images/polyflex.png'])
flex22=variant(polyflex,'Polyflex - 22G Blue',[('Gauge','22G'),('Colour','Blue'),('Catheter diameter','0.9 mm'),('Catheter length','25 mm'),('Flow rate','36 ml/min')],images=polyflex['image_paths'])
flex22['specifications']=[s for s in flex22['specifications'] if s['label'] not in ('Optional catheter','Documented size range')]
pur_flex=variant(polyflex,'Polyflex - PUR Catheter Option',notes=['Optional PUR catheter is explicitly documented. Exact gauge availability is not specified; do not infer a gauge/material cross-product.'])
pur_flex['description']='IV cannula with port, snap-fit cap and perforated wings; optional PUR catheter.'
pur_flex['specifications']=[{'label':'Documented catheter option','value':'PUR'}]
pur_flex['gaps'].append('Staff must verify the precise gauge and stock identifier for the PUR option')
safety_features=['Self-activating safety mechanism','Needle guard automatically covers the bevel after needle withdrawal','Colour-coded guard identification','Rounded grip on needle hub','Conventional IV-cannula insertion technique','Tapered kink-resistant FEP/PUR radiopaque catheter']
add('Polywin Safety',8,'IV Cannulas','Safety IV cannula without port and without wings.',safety_features,
    [('Documented size range','14G to 26G')],brand='POLYMED',kind='product_family',notes=['CONTRADICTION: title says without port, copied feature says injection port for code 11006. Omit port feature pending review. Code 11006 is not assigned as a SKU.'],images=['images/polywin-safety.png'])
polyflon=add('Polyflon',9,'IV Cannulas','IV cannula with port and wings with FEP catheter.',cannula_features+['Luer lock'],
    [('Standard catheter','FEP'),('Optional catheter','PUR'),('Documented size range','14G to 26G')],brand='POLYMED',kind='product_family',
    notes=['Unclear source phrase LATER FREE is omitted; do not silently convert it to a latex-free claim.'],images=['images/polyflon.png'])
flon20=variant(polyflon,'Polyflon - 20G Pink',[('Gauge','20G'),('Colour','Pink'),('Catheter diameter','1.1 mm'),('Catheter length','32 mm'),('Flow rate','56 ml/min')],images=polyflon['image_paths'])
flon20['specifications']=[s for s in flon20['specifications'] if s['label'] not in ('Optional catheter','Documented size range')]
pur_flon=variant(polyflon,'Polyflon - PUR Catheter Option',notes=['Optional PUR catheter is explicitly documented. Exact gauge availability is not specified; do not infer a gauge/material cross-product.'])
pur_flon['description']='IV cannula with port and wings; optional PUR catheter.'
pur_flon['specifications']=[{'label':'Documented catheter option','value':'PUR'}]
pur_flon['gaps'].append('Staff must verify the precise gauge and stock identifier for the PUR option')
add('Polysafety',9,'IV Cannulas','Safety IV cannula with snap-fit cap and perforated wings.',safety_features+['Injection port with snap-fit cap'],
    [('Documented size range','14G to 26G')],brand='POLYMED',kind='product_family',notes=['Generic code 11006 appears in multiple product descriptions; do not treat it as a unique SKU.'],images=['images/polysafety.png'])
add('Polycan Safety',10,'IV Cannulas','Safety IV cannula with wings, without port.',safety_features,
    [('Documented size range','14G to 26G')],brand='POLYMED',kind='product_family',notes=['CONTRADICTION: title says without port; generic feature lists a port for code 11006. Omit port feature pending review.'],images=['images/polycan-safety.png'])
spike=add('Polyspike',10,'Vial Access','Vial access spike.',
    ['Vented spike for withdrawing fluids from vials or semi-rigid containers','Safety snap cap reduces contamination','PVC free; DEHP free; latex free'],
    brand='POLYMED',kind='product_family',notes=['Safety-valve and snap-fit-cap presentations pictured for red, blue and green. No cross-product combinations beyond the six pictured presentations are inferred.'],images=['images/polyspike-safety-valve.png','images/polyspike-snap-fit.png'])
for letter,fluid,use in [('R','5 micron','Chemotherapeutic drugs'),('B','5 micron','Normal drugs'),('G','NA (as printed)','Normal drugs')]:
    for closure in ['Safety Valve','Snap-fit Cap']:
        variant(spike,f'Polyspike {letter} - {closure}',[('Fluid filter',fluid),('Air filter','0.1 micron'),('Nature of use',use),('Closure',closure)],notes=['Image shows multiple colours, so no individual variant image is assigned.'])
syringe_features=['Low dead space design','Clear transparent barrel with bold markings','Single-use syringe with integrated Japanese needle','Latex free; non-toxic; non-pyrogenic']
ira=add('Irasafety Syringe',11,'Syringes','Closed-barrel needle-retractable safety syringe.',
    ['Advanced Uni-Body design']+syringe_features,kind='product_family',notes=['Pack counts and needle dimensions transcribed from image-only table. Manufacturer is not stated.'],images=['images/irasafety-syringe.png'])
for volume,gauges,pack in [('1cc',['27G'],200),('2cc',['25G'],100),('3cc',['21G','23G'],100),('5cc',['21G','23G'],100),('10cc',['21G','23G'],100)]:
    for gauge in gauges:
        variant(ira,f'Irasafety Syringe - {volume} {gauge} x 1 inch',[('Capacity',volume),('Needle',gauge+' x 1 inch'),('Packaging units',str(pack))])
alph=add('Alphashot',11,'Syringes','Disposable sterile syringe for clinical drug-solution injection.',
    ['Medical-grade polypropylene','Sterilized by ETO gas']+syringe_features,kind='product_family',notes=['Needle variants are transcribed from the image-only table; no SKU, manufacturer or selling unit is implied by box count.'],images=['images/alphashot.png'])
needle_rows={
 '1ml':[('27G','1/2','0.40 x 12 mm'),('26G','5/8','0.45 x 16 mm'),('25G','1','0.50 x 25 mm')],
 '3ml':[('23G','1','0.60 x 25 mm'),('23G','1 1/4','0.60 x 30 mm'),('22G','1 1/4','0.70 x 30 mm'),('22G','1 1/2','0.70 x 38 mm'),('21G','1 1/4','0.80 x 30 mm')],
 '5ml':[('23G','1','0.60 x 25 mm'),('23G','1 1/4','0.60 x 30 mm'),('22G','1 1/4','0.70 x 30 mm'),('22G','1 1/2','0.70 x 38 mm'),('21G','1 1/2','0.80 x 38 mm')],
 '10ml':[('22G','1 1/4','0.70 x 30 mm'),('22G','1 1/2','0.70 x 38 mm'),('21G','1 1/2','0.80 x 38 mm')]}
for volume,needles in needle_rows.items():
    for gauge,length,metric in needles:
        variant(alph,f'Alphashot - {volume} {gauge} x {length} inch',[('Capacity',volume),('Needle',gauge+' x '+length+' inch'),('Needle dimensions',metric),('Units per box','100')])

# Preserve the brochure's diagnostic groupings even when clinically unusual.
# No regulatory badges on page 12 are assigned to individual candidates.
tests={
"Women's Health":[
'Rapiquick Pregnancy Midstream Device (Urine)','Rapiquick Pregnancy Cassette 10mIU/mL (S/P/U)','Rapiquick Pregnancy Cassette 20mIU/mL (S/P/U)','Rapiquick Pregnancy Cassette 25mIU/mL (S/P/U)','Rapiquick Pregnancy Strip 10mIU/mL (Urine)','Rapiquick Pregnancy Strip 25mIU/mL (Urine)','LH Ovulation Rapid Test Kit','FSH Rapid Test Kit'],
'TORCH Range':['Rapiquick Toxo Rapid Test Kit','Rapiquick Rubella Rapid Test Kit','Rapiquick CMV Rapid Test Kit','Rapiquick ToRCH IgG/IgM Rapid Test Kit','Rapiquick ToRCH Combo Rapid Test Kit'],
"Women\'s Health - Others":['Rapiquick Candida Albicans Rapid Test Kit','Rapiquick Neisseria Gonorrhea Rapid Test Kit','Rapiquick Chlamydia Trachomatics Rapid Test Kit','Rapiquick Chlamydia & Gonorrhea Rapid Test Kit','Rapiquick Strep B Rapid Test Kit'],
'Infectious':['Adenovirus & Rotavirus & Norovirus Rapid Test Kit','Rapiquick H.Pylori Antibody Rapid Test Kit','Rapiquick H.Pylori Antigen Rapid Test Kit','Rapiquick Zika IgG/IgM Rapid Test'],
'Tropical Diseases':['Rapiquick Chagas Rapid Test Kit','Chikugunya Rapid Test Kit','Rapiquick Dengue IgG/IgM Rapid Test Kit','Rapiquick Dengue NS1 Rapid Test Kit','Rapiquick Dengue Combo Rapid Test Kit','Rapiquick Filariasis Rapid Test Kit','Rapiquick Typhoid Rapid Test Kit','Rapiquick Salmonella typhi antigen Rapid Test Kit','Rapiquick Salmonella paratyphi antigen Rapid Test Kit','Rapiquick Leishmania Rapid Test Kit','Rapiquick Malaria Rapid Test Kit','Rapiquick Leptospira Rapid Test Kit'],
'Hepatitis Markers':['Hepatits A Rapid Test Kit','Rapiquick Hepatitis B (HBsAb) Rapid Test Device','Rapiquick Hepatitis B (HBsAg) Rapid Test Cassette','Rapiquick Hepatitis B (HBsAg) Rapid Test Strips','Rapiquick Hepatitis C (HCV) Rapid Test Cassette','Rapiquick Hepatitis C (HCV) Rapid Test Strips','Rapiquick HIV 1/2 Rapid Test Cassette','Rapiquick HIV 1/2 Rapid Test Strips','Rapiquick Syphilis Rapid Test Cassette','Rapiquick Syphilis Rapid Test Strips'],
'Respiratory Tract':['Strep A Rapid Test','Rapiquick Influenza A + B Rapid Test','Respiratory Syncytial Virus Antigen Rapid Test','RSV and Influenza A + B Rapid Test','Rapiquick Measles Virus Rapid Test'],
'Respiratory Tract - Others':['Rapiquick Tetanus Rapid Test','Rapiquick Tuberculosis Rapid Test'],
'Drug of Abuse':['Rapiquick THC50/MET1000 Drug of Abuse Rapid Test Panel','Rapiquick THC50/MET1000 Drug of Abuse Rapid Test Cassette','Rapiquick THC50/MET1000/MDMA500 Drug of Abuse Rapid Test Cassette','Rapiquick THC50/MET1000/MDMA500/COC300/MOP2000 Drug of Abuse Rapid Test Panel','Rapiquick THC50/MET1000/MDMA500/COC300/MOP2000 Drug of Abuse Rapid Test Cassette'],
'Tumor Markers':['Rapiquick Alpha Fetoprotein Rapid Test Kit','Rapiquick Carcinoembryonic Antigen Rapid Test Kit','Rapiquick Prostate Specific Antigen Rapid Test Kit','Rapiquick Fecal Occult Blood Rapid Test Kit','Rapiquick Transferrin & Hemoglobin and Hemoglobin-Haptoglobin Combo Rapid Test Kit','Rapiquick Hemoglobin and Hemoglobin-Haptoglobin Combo Rapid Test Kit'],
'Cardiac Marker':['Rapiquick Troponin I Rapid Test Kit','Rapiquick Troponin T Rapid Test Kit','Rapiquick CK-MB Rapid Test Kit','Rapiquick Myoglobin Rapid Test Kit','Myoglobin, CK-MB & Troponin I Combo Rapid Test Kit','H-FABP, Myoglobin/CK-MB/Troponin I Combo Rapid Test Kit','Rapiquick NT-proBNP Rapid Test Kit','Rapiquick D-Dimer Rapid Test Kit','Rapiquick C-reactive Protein Rapid Test Kit','Rapiquick Procalcitonin Rapid Test Kit'],
'Others':['Rapiquick Ferritin Rapid Test Kit','Rapiquick SP-10 Rapid Test Kit','Rapiquick Thyroid Stimulating Hormone Rapid Test Kit','Rapiquick Vitamin D Rapid Test Kit','Rapiquick RPR Screening Test','Rapiquick Bacterial Vaginosis (Variety)','Rapiquick Rheumatoid Factor Rapid Test Kit'],
'COVID Related - Antibody':['SARS-COV-2 IgG/IgM Rapid Test'],
'COVID Related - Antigen':['Hangzhou Alltest COVID-19 Antigen Rapid Test (Specimen: Nasopharyngeal Swab)','VCODE Encode SARS-COV-2 Rapid Test Device (Specimen: Throat Swab and Nasal Swab)']}
for group,names in tests.items():
    for name in names:
        brand = 'Rapiquick' if name.startswith('Rapiquick') else 'Hangzhou Alltest' if name.startswith('Hangzhou Alltest') else 'VCODE Encode' if name.startswith('VCODE') else None
        item=add(name,12,'Rapid Test Kits - '+group,brand=brand,notes=['Named listing only: confirm exact model, specimen, pack size, current approval and intended use before publication. No general FDA badge is imported.'])
        item['documented_diagnostic_category']=group
        if group=='Hepatitis Markers' and any(word in name for word in ('HIV','Syphilis')):
            item['review_notes'].append('Brochure groups this under Hepatitis Markers; staff should confirm clinical browsing category without changing the source provenance.')
        if any(word in name for word in ('Trachomatics','Hepatits','Chikugunya','(Variety)')):
            item['review_notes'].append('Source spelling or variant wording is ambiguous. Do not silently normalize medical identity.')

equipment={
(13,'Hospital Furniture'):['Hospital Bed','Double Crank Hospital Bed','Manual Crank 1 Function Hospital Bed','Manual Crank 3 Function Hospital Bed','Electric Function Bed','Electric operating table','Electrical Gynaecology Obstetric Operation Table','Overboard Table','Electro-Hydraulic Surgery Table','Manual Surgery Table','Emergency Cart','ER Stretcher','Ambulance Stretcher'],
(13,'Medical Freezers and Refrigerators'):['Vaccine Refrigerator','Blood Bank Refrigerator','Cooler / Freezer Combi','Lyophilizer','Medical Freezers','Outdoor Cooler - Freezers','Outdoor Cooler Equipment (Solar Box)','Outdoor Cooler - Ultra Deep Freezer','Ultra-Low Temperature Freezer','Eco Vaccine Refrigerator','Medical Waster Cabinet','Plasma Freezer','Laboratory Refrigerator'],
(13,'Radiology Equipment'):['Ceiling Suspension DR','Digital X-ray Radiographic System','Portable Ultrasound','Digital Mobile Radiography System','Full-Digital Color Doppler Diagnostic Ultrasound System','MRI','Digital Radiography Systems','Portable Mobile X-ray System','CT Scan','Digital Radiography System','Full-Field Digital Mammography System','Mammography System','Mobile C-arm','Mobile X-Ray System','Radiography System','Digital Portable X-ray machine'],
(13,'NICU Equipment'):['Baby Cart','Infant Incubator','Infant Radiant Warmer','Baby Cribs','Neonatal Led Phototherapy unit','Transport Infant Incubator'],
(14,'ER / OR / ICU Equipment'):['Defibrillator','Biphasic Defibrillator','Monitor Cardioverter Biphasic Defibrillator','Automated External Defibrillator','Electrosurgical Unit','Argon Coagulation unit','Shadowless Operating Lamp','Surgical LED Light','Infusion Pump','Syringe pump','Portable Ventilator','Mechanical Ventilator','Anesthesia Machine','Handheld Vital Sign Monitor (NIBP)','Vital Sign Monitor','Patient Monitor','High-flow heated respiratory humidifier','Chest Compressions Machine','Oxygen Concentration','Colonoscopes','Gastroscopy and Colonoscopy','High End Gyn & GS Laparoscopy','Laparoscopy with Hysteroscopy','Standard Gyn & GS Laparoscopy','Heavy Duty Mobile Suction Machine','Portable Suction Unit'],
(14,'Diagnostic Equipment'):['Fingertip Oximeter','3 channel ECG','12 channel ECG','Otoscope and Opthalmoscope','Fetal Doppler','Fetal or Maternal Monitor','Automatic Digital Non-Contact Thermometer','K9 Thermal Scanner'],
(14,'Laboratory Equipment'):['Tissue Embedding System','Mini Centrifuge','PRP Centrifuge','Microhematocrit centrifuge','Table Top Centrifuge','Universal Centrifuge','Desktop Low Speed Temperature Control Centrifuge','Floor Universal High-Speed Refrigerated Centrifuge','Blood Gas Analyzer','Auto Hematology Analyzer','Chemistry Analyzer','Powered Air Purifying Respirator (PAPR)','Vortex mixer','Biological Microscopes','High Quality Ductless Fume Hood','Biosafety Transport Box','Dry bath incubator','Micro Pette Mechanical Pipette','Analytical Balance','Digital Thermostatic Water Bath','Pcr hood workstation','Class II A2 Biological Safety Cabinet','Cell Smear Centrifuge','Microtome'],
(14,'Sterilization Equipment'):['Table Type Steam Sterilizer Infant Incubator','Vertical Pressure Steam Sterilizer','Autoclave','Hot Air Sterilization','Vertical Autoclave','Vertical Steam Autoclave','High Pressure Steam Autoclave','Air Purifier','Portable air cleaner HEPA filtration system','Uvion Air Asepticizer'],
(15,'ENT Equipment'):['Video laryngoscope - VL3D','Video laryngoscope - VL3R','Video laryngoscope - VLDM','Video laryngoscope - VLRM','Fiber Optic Laryngoscope Set','Laryngoscope set - Adult'],
(15,'Disaster and Emergency Offerings'):['Modular Shelter for evacuation center','Rescue Motorcycle / Ambulance','Field Hospital']}
for (page,category),names in equipment.items():
    for name in names:
        model = name.startswith('Video laryngoscope - ')
        kind = 'individual' if model else 'service_or_offering' if category=='Disaster and Emergency Offerings' else 'equipment_family'
        notes=['Named offering only. No undocumented model, manufacturer, specification, price or image is assigned.']
        if name=='High Quality Ductless Fume Hood':notes.append('Exact listing occurs twice on page 14; merged into one candidate, not two products.')
        if name in ('Digital Radiography Systems','Digital Radiography System','Radiography System','Digital X-ray Radiographic System'):
            notes.append('Possible overlapping radiography family; retain separate source wording for staff duplicate review.')
        if name=='Table Type Steam Sterilizer Infant Incubator':notes.append('Ambiguous combined listing: do not assume an infant incubator is a sterilizer or split into invented products.')
        if name in ('Medical Waster Cabinet','Oxygen Concentration','Overboard Table','Otoscope and Opthalmoscope'):
            notes.append('Unclear or misspelled source wording requires staff confirmation before naming an individual product.')
        item=add(name,page,category,kind=kind,notes=notes)
        if model:item['specifications']=[{'label':'Model as printed','value':name.split(' - ')[1]}]
        if name=='High Quality Ductless Fume Hood':item['source_occurrences']=2


def extract_images():
    import pypdfium2 as pdfium
    target=FOLDER/'images';target.mkdir(exist_ok=True)
    mapping={3:{2:'alpha-care-adult-diaper',4:'alpha-care-underpads-front',5:'alpha-care-underpads-side'},
      4:{3:'glucoseth-kit',8:'polyvol'},5:{4:'autofusion',9:'microfusion'},6:{4:'oncofusion',10:'photofusion'},
      7:{4:'blood-administration',9:'haemofusor'},8:{3:'polyflex',8:'polywin-safety'},9:{4:'polyflon',8:'polysafety'},
      10:{4:'polycan-safety',8:'polyspike-safety-valve',9:'polyspike-snap-fit'},11:{4:'irasafety-syringe',12:'alphashot'}}
    document=pdfium.PdfDocument(str(PDF)); image_index=[]
    for number,objects in mapping.items():
        page=document[number-1]
        for index,obj in enumerate(page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE])):
            if index not in objects:continue
            filename='images/'+objects[index]+'.png'
            bitmap=obj.get_bitmap()
            image=bitmap.to_pil()
            image.save(FOLDER/filename)
            image_index.append({'path':filename,'page':number,'pdf_image_object_index':index,'width':image.width,'height':image.height,
                                'bytes':(FOLDER/filename).stat().st_size,'review':'Correct product panel visually identified; staff must approve clarity and exact variant association'})
        page.close()
    document.close()
    return image_index


def main():
    images=extract_images()
    image_info={image['path']:image for image in images}
    for item in rows:
        if any(image_info[path]['bytes']>200000 for path in item['image_paths']):
            item['image_review_status']='Source image exceeds the 200 KB upload limit; import without imagery and upload a reviewed replacement'
            item['review_notes'].append('Original source PNG exceeds the upload size limit. Do not bypass validation; request an approved replacement.')
        elif any(min(image_info[path]['width'],image_info[path]['height'])<150 for path in item['image_paths']):
            item['image_review_status']='Low-resolution source diagram/image; staff must approve clarity or supply a replacement'
    manifest={'schema_version':1,'source_pdf':PDF.name,'source_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
      'page_count':15,'page_numbering':'1-based physical PDF pages (each is a two-panel spread)',
      'review':'All 15 rendered pages and extracted text reviewed. Page 11 image-only tables transcribed at increased resolution. Every record remains unapproved.',
      'policy':'Documentation manifest only. Never seed active products, stock or prices. Candidate IDs are not SKUs. Images require separate staff approval.',
      'counts':dict(Counter(item['candidate_type'] for item in rows)),
      'excluded_content':['Pages 1-2 company/promotional content','Category headings','And many more entries','General service/training paragraphs','Unrelated centrifuge paragraph under Glucoseth','Company ISO/FDA badges: not product-level approvals','Generic disaster-kit photograph: no identifiable individual product'],
      'images':images,'candidates':rows}
    (FOLDER/'import-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# Brochure review manifest','',f"Source: {PDF.name}; SHA-256: `{manifest['source_sha256']}`.",'',
      f'{len(rows)} review records. Counts: '+json.dumps(manifest['counts'])+'.','',
      'No record is approved. SKU and selling unit must come from staff. Families and services are not directly importable. Source images remain review assets, never automatically published.','',
      '| Review key | Page | Product / offering | Type | Documented brand | Review notes |','|---|---:|---|---|---|---|']
    for row in rows:
        lines.append('| '+ ' | '.join([row['candidate_id'],str(row['source_pdf_page']),row['name'],row['candidate_type'],row['documented_brand'] or 'Not stated','; '.join(row['review_notes']).replace('|','/')])+' |')
    (FOLDER/'MANIFEST_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'records':len(rows),'counts':manifest['counts'],'images':len(images)},indent=2))


if __name__=='__main__':main()
