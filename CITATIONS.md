# Citations and Research Attribution

This software incorporates research methods and code from academic sources that require proper attribution when using or distributing this application.

## Primary Research Citation

When using the AASHTO CDA (Cumulative Difference Approach) method in this software, please cite:

**Katicha, S., Flintsch, G. (2025)**  
*"Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation"*  
Transportation Research Record, Accepted.

## Software License and Copyright

### AASHTO CDA Implementation

The AASHTO CDA method implementation (`src/analysis/methods/aashto_cda.py`) is distributed under the BSD 2-Clause License:

**Copyright (c) 2025, Samer Katicha**

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## Implementation Notes

### MATLAB to Python Translation

The AASHTO CDA implementation is a Python translation of the original MATLAB research code, with the following adaptations:

- Converted from MATLAB 1-based to Python 0-based indexing
- Replaced MATLAB functions with numpy/scipy equivalents  
- Maintained identical algorithm logic and statistical computations

### Statistical Foundation

The AASHTO CDA method is based on:

**AASHTO Guide for the Local Calibration of the Mechanistic-Empirical Pavement Design Guide**  
*Chapter on Data Analysis and Segmentation*

## Usage in Academic Work

When using this software in academic research, please:

1. **Cite the primary research** (Katicha & Flintsch, 2025) when using AASHTO CDA results
2. **Acknowledge the software** if using the complete Highway Segmentation GA framework
3. **Respect the BSD license terms** for any code redistribution

## Additional Documentation

For detailed technical information about the AASHTO CDA method:
- See `docs/AASHTO_CDA_USER_GUIDE.md` for implementation details
- See `docs/AashtoCDADocs/` for original MATLAB reference implementation

---

*Last updated: April 2026*