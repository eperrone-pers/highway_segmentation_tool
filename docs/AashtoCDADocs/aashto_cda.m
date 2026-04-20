function [uniform_sections,nodes,Section_Start,Section_End,mu] = aashto_cda(y,alpha,num_sections,min_length,min_section_difference,method,GlobalLocal)
%
% Performs segmentation of data into uniform sections
%
% Inputs:
%  Required Inputs:
%   - y: one-dimensional vector of data to be segmented
%  Optional Inputs:
%   - alpha       : Significance level; default=0.05 (Works for alpha < 0.5)
%   - num_sections: Maximum Number of segments; default length of vector y
%   - min_length  : Minimum length of segments. This corresponds to the
%                   minimum number of datapoints in each segment; default=1
%   - min_section_difference: minimum difference in the average of two
%                   adjacent segments; default=0
%   - method      : Method used to estimate the standard deviation of the
%                   random error; default uses difference sequence and
%                   assumes normally distributed error.
%                   method = 1: uses difference sequence and assumes
%                               normally distributed error
%                   method = 2: uses difference sequence (general error distribution)
%                   method = any other number: uses standard deviation of measurements (general error distribution)
%   - GlobalLocal : If GlobalLocal = 1, algorithm uses length of each
%                   segment in calculations (should be used and default)
%                   If GlobalLocal != 1, algorithm uses length of data in
%                   calculations (not recommended)
%
% Outputs:
%   - uniform_sections: Segmented data
%   - nodes           : Identified break points
%   - Section_Start   : Vector continaing the start of segments
%   - Section_End     : Vector continaing the end of segments
%   - mu              : Vector continaing the average of segments

% BSD 2-Clause License
% 
% Copyright (c) 2025, Samer Katicha
% 
% Redistribution and use in source and binary forms, with or without
% modification, are permitted provided that the following conditions are met:
% 
% 1. Redistributions of source code must retain the above copyright notice,
% this list of conditions and the following disclaimer.
% 
% 2. Redistributions in binary form must reproduce the above copyright notice,
% this list of conditions and the following disclaimer in the documentation
% and/or other materials provided with the distribution.
% 
% THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
% AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
% IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
% ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
% LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
% CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
% SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
% INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
% CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
% ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
% THE POSSIBILITY OF SUCH DAMAGE.
%
% To cite the work:
% Katicha, S., Flintsch, G. (2025), "Enhanced AASHTO Cumulative Difference
% Approach (CDA) for Pavement Data Segmentation" Transportation Research
% Record, Accepted.

if nargin<7
    GlobalLocal = 1;
    if nargin<6
        method = 2;
        if nargin<5
            min_section_difference = 0;
            if nargin<4
                min_length = 1;
                if nargin<3
                    num_sections = length(y);
                    if nargin<2
                        alpha = 0.05;
                    end
                end
            end
        end
    end
end

y        = y(:);
x        = 1:length(y);
x        = x(:);
cy       = cumsum(y);
nodes    = zeros(size(y));
nodes(1) = x(1);
nodes(2) = x(end);

if method==1
    sigma = 1.4826*mad(diff(y),1)/sqrt(2);
elseif method==2
    sigma = std(diff(y))/sqrt(2);
else
    sigma = std(y);
end

for i=2:num_sections+1
    [location,change_point] = test_change_point(cy,nodes(1:i),x,sigma,alpha,min_length,GlobalLocal);
    if change_point==0
        break;
    end
    nodes(i+1) = location;
    snodes     = sort(nodes(1:i + 1));
    if all(diff(snodes)<(2*min_length - 1))
        break
    end
end
ii = i;
uniform_sections = diff(interp1(nodes(1:ii),cy(nodes(1:ii)), x));
uniform_sections = [uniform_sections(1); uniform_sections];
nodes            = sort(nodes(1:ii));
Section_End      = nodes(2:end);
Section_Start    = [1; Section_End(1:end - 1) + 1];

mu = zeros(length(Section_Start),1);

if min_section_difference>0
    
    for i=1:length(Section_Start)
        mu(i) = mean(y(Section_Start(i):Section_End(i)));
    end
    
    [MinChange,ID] = min(abs(diff(mu)));
    
    while MinChange<min_section_difference
        Section_Start(ID+1) = [];
        Section_End(ID)     = [];
        mu(ID)              = [];
        mu(ID)              =  mean(y(Section_Start(ID):Section_End(ID)));
        [MinChange,ID]      = min(abs(diff(mu)));
    end
    
    nodes            = [1;Section_End];
    uniform_sections = diff(interp1(nodes(1:end),cy(nodes(1:end)), x));
    uniform_sections = [uniform_sections(1); uniform_sections];

end

end

function [location,change_point_test,M,th] = test_change_point(cy,nodes,x,sigma,alpha,min_length,GlobalLocal)
% test the presence of change points in the signal cy for all sections
% defined by the points given in nodes
% Input:
% - cy: cumulative sum of measurements
% - nodes: locations of currently identified change points
% - sigma: error standard deviation
% - alpha: significance level
% - min_length: minimum section length
% Output:
% - location: index of candidate cahnge point
% - change_point_test: test results whether the detected change point is
%                      significant (0 for no, 1 for yes)

nodes     = sort(nodes);
L         = diff(nodes);
m         = zeros(size(L));
id        = zeros(size(L));
cy_interp = interp1(nodes,cy(nodes),x);
th        = sqrt(-1/2*log(alpha/(length(L))/2));

change_point_test = 0;

for i=1:length(L)
    cda                = cy(nodes(i):nodes(i+1)) - cy_interp(nodes(i):nodes(i+1));
    [V,ID]             = sort(abs(cda),'descend');
    for j=1:length(ID)
        if min(abs(ID(j)-[1; nodes(i+1) - nodes(i) + 1]))>(min_length - 1)
            id(i) = ID(j);
            m(i)  = V(j);
            break
        end
    end
end

if GlobalLocal==1
    [M,idx] = max(m/sigma./sqrt(max(L,1)));
else
    [M,idx] = max(m/sigma/sqrt(length(cy)));
end
location    = id(idx)+sum(L(1:idx - 1));

if M>th
    change_point_test = 1;
end

end