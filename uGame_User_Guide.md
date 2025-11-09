# uGame QA Add-on for Blender

# 

# User Guide

1. ### Introduction

   The uGame QA Add-on is designed to help product reviewers validate Game-Ready categorized assets. It automates checks for geometry, UVs, textures, and rigging, producing a structured report that highlights issues for the creator to action and help understand Game-Ready requirements in game engines.

   

2. ### Installation

* Go to Edit \> Preferences \> Add-ons \> Install from Disk.  
* Select the .zip file for uGame.  
* Enable the add-on  
  You’ll now see the uGame button on the header bar.

3. ### Settings Overview

* **Exclude High-Poly**: Excludes objects in a collection named high poly or objects with a \_high suffix (enabled by default).  
* **Asset Collection Mode**: For scanning asset collections or modular asset collections.  
* **AAA Game Check**: Stricter protocols. E.g. Texture naming convention, Texture map requirements.  
* **Hero Asset**: Enable for hero assets, allows higher resolution textures.  
* **Scan Mode**:  
  * OBJECT \- check single mesh object  
  * COLLECTION \- check all assets in a collection, including nested collections.  
  * FILE \- check every object in the entire file.

4. ### Running a QA Scan

* Select the object or collection.  
* Click the uGame button  
* Select settings and click OK  
* Review the structured report

5. ### Report Sections

* **Geometry**  
  * Vertex Count  
  * Face Count  
  * Edge Count  
  * N-gons  
  * Non-Manifold Edges  
  * Stray Vertices  
  * Transforms Applied  
  * Normals  
  * Double Vertices  
* **Textures**  
  * Texture Name  
  * Texture Resolution  
  * Required Maps  
  * Optional Maps  
* **UVs**  
  * UV Unwrapped  
  * Marked Seams  
  * UV Island Count  
  * Texel Density Ratio  
  * Texel Density Average  
  * Texel Density Deviation  
  * UV Space Utilization  
* **Modifiers**  
  * Allowed Modifiers  
* **Rigging**  
  * Bone Naming  
  * Hierarchy Clean  
  * Bone Count  
  * Constraints Present  
  * Drivers Present

6. ### Color Atlas Detection

* Color Atlas confidence score to identify color atlas usage.   
  Score \>= 5 out of 6 indicates likeliness of Color Atlas use.  
  * UV Utilization \< 10  
  * Texel Density Ratio \< 0.1  
  * UV Island Count \< 10  
  * No Marked Seams  
  * No Normal Map  
  * No Roughness Map

7. ### Tips

* **Simple Meshes**: One UV island is acceptable if geometry is \< 100 faces.  
* **Color Atlas**: Collapsed, Bad UV unwrapping or Missing Maps may give false positives.

8. ### Output Levels

* **INFO**: Pass or acceptable condition  
* **WARNING**: May need to be reviewed  
* **ERROR**: Must be fixed prior to resubmission

9. ### Conclusion

   The uGame QA Add-on balances technical rigor with creator empathy. Reports are designed to be transparent, actionable and respectful of different asset workflows, whether hero assets, background props, modular asset collections or stylized color atlas texturing.